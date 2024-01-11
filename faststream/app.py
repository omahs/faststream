import logging
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

import anyio
from typing_extensions import ParamSpec

from faststream._compat import ExceptionGroup
from faststream.cli.supervisors.utils import HANDLED_SIGNALS
from faststream.log import logger
from faststream.types import AnyDict, AsyncFunc, Lifespan, SettingField
from faststream.utils import apply_types, context
from faststream.utils.functions import drop_response_type, fake_context, to_async

P_HookParams = ParamSpec("P_HookParams")
T_HookReturn = TypeVar("T_HookReturn")


if TYPE_CHECKING:
    from pydantic import AnyHttpUrl

    from faststream.asyncapi.schema import (
        Contact,
        ContactDict,
        ExternalDocs,
        ExternalDocsDict,
        License,
        LicenseDict,
        Tag,
        TagDict,
    )
    from faststream.broker.core.broker import BrokerUsecase


class FastStream:
    """A class representing a FastStream application.

    Attributes:
        _on_startup_calling : list of async functions to be called on startup
        _after_startup_calling : list of async functions to be called after startup
        _on_shutdown_calling : list of async functions to be called on shutdown
        _after_shutdown_calling : list of async functions to be called after shutdown

    Methods:
        __init__ : initializes the FastStream application
        on_startup : adds a hook to run before the broker is connected
        on_shutdown : adds a hook to run before the broker is disconnected
        after_startup : adds a hook to run after the broker is connected
        after_shutdown : adds a hook to run after the broker is disconnected
        run : runs the FastStream application
        _start : starts the FastStream application
        _stop : stops the FastStream application
        _startup : runs the startup hooks
        _shutdown : runs the shutdown hooks
        __exit : exits the FastStream application
    """

    _on_startup_calling: List[AsyncFunc]
    _after_startup_calling: List[AsyncFunc]
    _on_shutdown_calling: List[AsyncFunc]
    _after_shutdown_calling: List[AsyncFunc]

    def __init__(
        self,
        broker: Optional["BrokerUsecase[Any, Any]"] = None,
        logger: Optional[logging.Logger] = logger,
        lifespan: Optional[Lifespan] = None,
        # AsyncAPI args,
        title: str = "FastStream",
        version: str = "0.1.0",
        description: str = "",
        terms_of_service: Optional["AnyHttpUrl"] = None,
        license: Optional[Union["License", "LicenseDict", AnyDict]] = None,
        contact: Optional[Union["Contact", "ContactDict", AnyDict]] = None,
        identifier: Optional[str] = None,
        tags: Optional[Sequence[Union["Tag", "TagDict", AnyDict]]] = None,
        external_docs: Optional[
            Union["ExternalDocs", "ExternalDocsDict", AnyDict]
        ] = None,
    ) -> None:
        """Asynchronous FastStream Application class.

        stores and run broker, control hooks

        Args:
            broker: async broker to run (may be `None`, then specify by `set_broker`)
            logger: logger object to log startup/shutdown messages (`None` to disable)
            lifespan: lifespan context to run application
            title: application title - for AsyncAPI docs
            version: application version - for AsyncAPI docs
            description: application description - for AsyncAPI docs
            terms_of_service: application terms of service - for AsyncAPI docs
            license: application license - for AsyncAPI docs
            contact: application contact - for AsyncAPI docs
            identifier: application identifier - for AsyncAPI docs
            tags: application tags - for AsyncAPI docs
            external_docs: application external docs - for AsyncAPI docs
        """
        self.broker = broker
        self.logger = logger
        self.context = context
        context.set_global("app", self)

        self._on_startup_calling = []
        self._after_startup_calling = []
        self._on_shutdown_calling = []
        self._after_shutdown_calling = []

        self.lifespan_context = (
            apply_types(
                func=lifespan,
                wrap_model=drop_response_type,
            )
            if lifespan is not None
            else fake_context
        )

        # AsyncAPI information
        self.title = title
        self.version = version
        self.description = description
        self.terms_of_service = terms_of_service
        self.license = license
        self.contact = contact
        self.identifier = identifier
        self.asyncapi_tags = tags
        self.external_docs = external_docs

    def set_broker(self, broker: "BrokerUsecase[Any, Any]") -> None:
        """Set already existed App object broker.

        Useful then you create/init broker in `on_startup` hook.
        """
        self.broker = broker

    def on_startup(
        self,
        func: Callable[P_HookParams, T_HookReturn],
    ) -> Callable[P_HookParams, T_HookReturn]:
        """Add hook running BEFORE broker connected.

        This hook also takes an extra CLI options as a kwargs

        Args:
            func: async or sync func to call as a hook

        Returns:
            Async version of the func argument
        """
        self._on_startup_calling.append(apply_types(to_async(func)))
        return func

    def on_shutdown(
        self,
        func: Callable[P_HookParams, T_HookReturn],
    ) -> Callable[P_HookParams, T_HookReturn]:
        """Add hook running BEFORE broker disconnected.

        Args:
            func: async or sync func to call as a hook

        Returns:
            Async version of the func argument
        """
        self._on_shutdown_calling.append(apply_types(to_async(func)))
        return func

    def after_startup(
        self,
        func: Callable[P_HookParams, T_HookReturn],
    ) -> Callable[P_HookParams, T_HookReturn]:
        """Add hook running AFTER broker connected.

        Args:
            func: async or sync func to call as a hook

        Returns:
            Async version of the func argument
        """
        self._after_startup_calling.append(apply_types(to_async(func)))
        return func

    def after_shutdown(
        self,
        func: Callable[P_HookParams, T_HookReturn],
    ) -> Callable[P_HookParams, T_HookReturn]:
        """Add hook running AFTER broker disconnected.

        Args:
            func: async or sync func to call as a hook

        Returns:
            Async version of the func argument
        """
        self._after_shutdown_calling.append(apply_types(to_async(func)))
        return func

    async def run(
        self,
        log_level: int = logging.INFO,
        run_extra_options: Optional[Dict[str, SettingField]] = None,
    ) -> None:
        """Run FastStream Application.

        Args:
            log_level: force application log level
            run_extra_options: extra options for running the app

        Returns:
            Block an event loop until stopped
        """
        assert self.broker, "You should setup a broker"  # nosec B101

        async with self.lifespan_context(**(run_extra_options or {})):
            try:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(self._start, log_level, run_extra_options)
                    await self._stop(log_level)
                    tg.cancel_scope.cancel()
            except ExceptionGroup as e:
                for ex in e.exceptions:
                    raise ex from None

    async def _start(
        self,
        log_level: int = logging.INFO,
        run_extra_options: Optional[Dict[str, SettingField]] = None,
    ) -> None:
        """Start the FastStream app.

        Args:
            log_level (int): log level (default: logging.INFO)
            run_extra_options (Optional[Dict[str, SettingField]]): extra options for running the app (default: None)

        Returns:
            None
        """
        self._log(log_level, "FastStream app starting...")
        await self._startup(**(run_extra_options or {}))
        self._log(
            log_level, "FastStream app started successfully! To exit, press CTRL+C"
        )

    async def _stop(self, log_level: int = logging.INFO) -> None:
        """Stop the application gracefully.

        Blocking method (waits for SIGINT/SIGTERM).

        Args:
            log_level (int): log level for logging messages (default: logging.INFO)

        Returns:
            None
        """
        with anyio.open_signal_receiver(*HANDLED_SIGNALS) as signals:
            async for _ in signals:
                self._log(log_level, "FastStream app shutting down...")
                await self._shutdown()
                self._log(log_level, "FastStream app shut down gracefully.")
                return

    async def _startup(self, **run_extra_options: SettingField) -> None:
        """Executes startup tasks.

        Args:
            run_extra_options: Additional options to be passed to the startup tasks.

        Returns:
            None
        """
        for func in self._on_startup_calling:
            await func(**run_extra_options)

        if self.broker is not None:
            await self.broker.start()

        for func in self._after_startup_calling:
            await func()

    async def _shutdown(self) -> None:
        """Executes shutdown tasks.

        Returns:
            None
        """
        for func in self._on_shutdown_calling:
            await func()

        if self.broker is not None:
            await self.broker.close()

        for func in self._after_shutdown_calling:
            await func()

    def _log(self, level: int, message: str) -> None:
        """Logs a message with the specified log level.

        Args:
            level (int): The log level.
            message (str): The message to be logged.

        Returns:
            None
        """
        if self.logger is not None:
            self.logger.log(level, message)

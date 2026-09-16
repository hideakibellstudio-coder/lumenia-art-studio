from __future__ import annotations
from typing import Type, TypeVar

T = TypeVar("T")


class ServiceRegistry:
    """
    Registro global de serviços para comunicação desacoplada entre plugins.

    Permite que um plugin registre uma implementação de um contrato (ABC) e
    outros plugins consultem essa implementação sem import direto.

    Exemplo de uso:
        # Registrar (feito pelo WorkspaceCore durante activate()):
        ServiceRegistry.instance().register(WorkspaceService, self)

        # Consultar (feito por um plugin de UI durante activate()):
        ws = ServiceRegistry.instance().get(WorkspaceService)
        ws.add_panel("brush", "Pincel", BrushDock(), area="left")
    """

    _instance: "ServiceRegistry | None" = None

    @classmethod
    def instance(cls) -> "ServiceRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        # {ServiceClass → [implementation_instance, ...]}
        self._registry: dict[type, list] = {}

    # ── Registro ──────────────────────────────────────────────────────────

    def register(self, service_class: Type[T], implementation: T) -> None:
        """
        Registra uma implementação para o contrato de serviço especificado.
        Múltiplas implementações do mesmo contrato são permitidas.

        Args:
            service_class:   O ABC ou tipo que define o contrato (ex.: WorkspaceService).
            implementation:  A instância que implementa o contrato.
        """
        if service_class not in self._registry:
            self._registry[service_class] = []
        if implementation not in self._registry[service_class]:
            self._registry[service_class].append(implementation)

    # Alias de compatibilidade com chamadas existentes em código legado
    def register_service(self, service_class: Type[T], implementation: T) -> None:
        """Alias de register() mantido para compatibilidade retroativa."""
        self.register(service_class, implementation)

    def unregister(self, service_class: Type[T], implementation: T) -> None:
        """Remove uma implementação específica do registro."""
        if service_class in self._registry:
            try:
                self._registry[service_class].remove(implementation)
            except ValueError:
                pass

    # Alias de compatibilidade
    def unregister_service(self, service_class: Type[T], implementation: T) -> None:
        """Alias de unregister() mantido para compatibilidade retroativa."""
        self.unregister(service_class, implementation)

    # ── Consulta ──────────────────────────────────────────────────────────

    def get(self, service_class: Type[T]) -> T | None:
        """
        Retorna a primeira implementação registrada para o serviço especificado.
        Retorna None se nenhuma implementação estiver registrada.
        """
        impls = self._registry.get(service_class, [])
        return impls[0] if impls else None

    def get_all(self, service_class: Type[T]) -> list[T]:
        """Retorna todas as implementações registradas para o serviço especificado."""
        return list(self._registry.get(service_class, []))

    # Alias de compatibilidade
    def get_services(self, service_class: Type[T]) -> list[T]:
        """Alias de get_all() mantido para compatibilidade retroativa."""
        return self.get_all(service_class)

    def has(self, service_class: type) -> bool:
        """Retorna True se houver ao menos uma implementação registrada."""
        return bool(self._registry.get(service_class))

    def clear(self) -> None:
        """Limpa todo o registro. Usado principalmente em testes."""
        self._registry.clear()


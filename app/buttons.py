from dataclasses import dataclass, field
from typing import Optional


def btn_style(color: str, outline: bool) -> str:
    prefix = 'btn-outline' if outline else 'btn'
    return f'{prefix}-{color}'


@dataclass
class Button:
    label: str
    icon: Optional[str] = None
    color: str = 'secondary'
    outline: bool = True
    size: str = 'sm'
    cls: str = ''
    extra: str = ''
    label_pos: str = 'right'
    confirm_msg: Optional[str] = None
    endpoint: Optional[str] = None
    url: Optional[str] = None
    method: str = 'GET'
    show_if: Optional[tuple] = None
    hide_if: Optional[tuple] = None
    url_var: str = 'id'
    extra_params: Optional[dict] = None
    position: str = 'nav_right'

    def btn_cls(self) -> str:
        return btn_style(self.color, self.outline)


@dataclass
class ConfirmModal:
    title: str
    message: str
    confirm_label: str = 'Confirmar'
    confirm_color: str = 'danger'
    cancel_label: str = 'Cancelar'
    icon: Optional[str] = 'trash.svg'


CONFIRM_EXCLUIR = ConfirmModal(
    title='Excluir registro',
    message='Tem certeza que deseja excluir?',
)
CONFIRM_REMOVER_ITEM = ConfirmModal(
    title='Remover item',
    message='Remover este item da lista?',
    confirm_label='Remover',
)


BTN_SALVAR = Button(label='Salvar', color='success', outline=False, cls='btn-success')
BTN_ENVIAR = Button(label='Enviar', icon='send.svg', color='success', outline=True, cls='btn-outline-success')
BTN_EXCLUIR = Button(label='Excluir', icon='trash.svg', color='danger', outline=False, cls='btn-danger', confirm_msg='Confirmar exclusão?')
BTN_NOVO = Button(label='+ Novo', color='success', outline=False, cls='btn-success')
BTN_VOLTAR = Button(label='Voltar', color='secondary', outline=True, cls='btn-outline-secondary')
BTN_EDITAR = Button(label='Editar', icon='pencil.svg', color='primary', outline=True, cls='btn-outline-primary')
BTN_CANCELAR = Button(label='Cancelar', color='secondary', outline=True, cls='btn-outline-secondary')
BTN_CONVERTER = Button(label='Converter', color='success', outline=False, cls='btn-success')
BTN_LISTA = Button(label='Lista', icon='list.svg', color='secondary', outline=True, cls='btn-outline-secondary')
BTN_IMPRIMIR = Button(label='Imprimir', icon='send.svg', color='secondary', outline=True, cls='btn-outline-secondary')
BTN_DETALHES = Button(label='Detalhes', color='info', outline=True, cls='btn-outline-info')
BTN_ADICIONAR = Button(label='+ Adicionar', color='success', outline=True, cls='btn-outline-success')
BTN_ADICIONAR_ITEM = Button(label='+ Adicionar Item', color='success', outline=True, cls='btn-outline-success')
BTN_FINALIZAR = Button(label='Finalizar', color='success', outline=False, cls='btn-success')
BTN_ATUALIZAR = Button(label='Atualizar', color='warning', outline=True, cls='btn-outline-warning')
BTN_REMOVER = Button(label='Remover', icon='minus-circle.svg', color='danger', outline=True, cls='btn-outline-danger', confirm_msg='Remover este item?')
BTN_SIM = Button(label='Sim, continuar logado', color='primary', outline=False, cls='btn-primary')
BTN_NAO = Button(label='Não', color='secondary', outline=True, cls='btn-outline-secondary')
BTN_LIMPAR = Button(label='Limpar', color='danger', outline=True, cls='btn-outline-danger')
BTN_APLICAR = Button(label='Aplicar', color='primary', outline=False, cls='btn-primary')
BTN_OK = Button(label='OK', color='danger', outline=False, cls='btn-danger')
BTN_SAIR = Button(label='Sair', color='danger', outline=True, cls='btn-outline-danger', confirm_msg='Descartar alterações?')
BTN_RENOVAR = Button(label='Renovar', color='info', outline=False, cls='btn-info')
BTN_RELATORIO = Button(label='Relatório', color='info', outline=True, cls='btn-outline-info')
BTN_GERAR = Button(label='Gerar', color='success', outline=False, cls='btn-success')
BTN_CONFIRMAR = Button(label='Confirmar', color='success', outline=False, cls='btn-success')
BTN_EDITAR_PRODUTO = Button(label='Editar Produto', icon='pencil.svg', color='primary', outline=True, cls='btn-outline-primary')
BTN_ENTRAR = Button(label='Entrar', color='danger', outline=False, cls='btn-danger')
BTN_ACESSAR = Button(label='Acessar', color='danger', outline=False, cls='btn-danger')

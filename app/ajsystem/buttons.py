from dataclasses import dataclass, field
from typing import Optional


def btn_style(color: str, outline: bool, size: str = 'sm') -> str:
    base = f'btn-{color} btn-{size}'
    return f'{base} btn-outline' if outline else base


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
    on_off: bool = False
    field: Optional[str] = None
    label_off: Optional[str] = None
    icon_off: Optional[str] = None

    def btn_cls(self) -> str:
        return self.cls or btn_style(self.color, self.outline, self.size)


@dataclass
class ConfirmModal:
    title: str
    message: str
    confirm_label: str = 'Confirmar'
    confirm_color: str = 'danger'
    cancel_label: str = 'Cancelar'
    icon: Optional[str] = 'trash'


CONFIRM_EXCLUIR = ConfirmModal(
    title='Excluir registro',
    message='Tem certeza que deseja excluir?',
)
CONFIRM_REMOVER_ITEM = ConfirmModal(
    title='Remover item',
    message='Remover este item da lista?',
    confirm_label='Remover',
)


BTN_SALVAR = Button(label='Salvar', icon='check', color='success', outline=False, cls='btn-success btn-sm')
BTN_ENVIAR = Button(label='Enviar', icon='paper-airplane', color='success', outline=True, cls='btn-outline btn-success btn-sm')
BTN_EXCLUIR = Button(label='Excluir', icon='trash', color='danger', outline=False, cls='btn-danger btn-sm', confirm_msg='Confirmar exclusão?')
BTN_NOVO = Button(label='+ Novo', color='success', outline=False, cls='btn-success btn-sm')
BTN_VOLTAR = Button(label='Voltar', color='secondary', outline=True, cls='btn-outline btn-secondary btn-sm')
BTN_EDITAR = Button(label='Editar', icon='pencil-square', color='primary', outline=True, cls='btn-outline btn-primary btn-sm')
BTN_CANCELAR = Button(label='Cancelar', color='secondary', outline=True, cls='btn-outline btn-secondary btn-sm')
BTN_CONVERTER = Button(label='Converter', icon='arrow-path', color='success', outline=False, cls='btn-success btn-sm')
BTN_LISTA = Button(label='Lista', icon='clipboard-document-list', color='secondary', outline=True, cls='btn-outline btn-secondary btn-sm')
BTN_IMPRIMIR = Button(label='Imprimir', icon='printer', color='secondary', outline=True, cls='btn-outline btn-secondary btn-sm')
BTN_DETALHES = Button(label='Detalhes', icon='eye', color='info', outline=True, cls='btn-outline btn-info btn-sm')
BTN_ADICIONAR = Button(label='+ Adicionar', color='success', outline=True, cls='btn-outline btn-success btn-sm')
BTN_ADICIONAR_ITEM = Button(label='+ Adicionar Item', color='success', outline=True, cls='btn-outline btn-success btn-sm')
BTN_FINALIZAR = Button(label='Finalizar', color='success', outline=False, cls='btn-success btn-sm')
BTN_ATUALIZAR = Button(label='Atualizar', icon='arrow-path', color='warning', outline=True, cls='btn-outline btn-warning btn-sm')
BTN_REMOVER = Button(label='Remover', icon='minus', color='danger', outline=True, cls='btn-outline btn-danger btn-sm', confirm_msg='Remover este item?')
BTN_SIM = Button(label='Sim, continuar logado', color='primary', outline=False, cls='btn-primary btn-sm')
BTN_NAO = Button(label='Não', color='secondary', outline=True, cls='btn-outline btn-secondary btn-sm')
BTN_LIMPAR = Button(label='Limpar', color='danger', outline=True, cls='btn-outline btn-danger btn-sm')
BTN_APLICAR = Button(label='Aplicar', color='primary', outline=False, cls='btn-primary btn-sm')
BTN_OK = Button(label='OK', color='danger', outline=False, cls='btn-danger btn-sm')
BTN_SAIR = Button(label='Sair', color='danger', outline=True, cls='btn-outline btn-danger btn-sm', confirm_msg='Descartar alterações?')
BTN_RENOVAR = Button(label='Renovar', color='info', outline=False, cls='btn-info btn-sm')
BTN_RELATORIO = Button(label='Relatório', icon='document-text', color='info', outline=True, cls='btn-outline btn-info btn-sm')
BTN_GERAR = Button(label='Gerar', color='success', outline=False, cls='btn-success btn-sm')
BTN_CONFIRMAR = Button(label='Confirmar', color='success', outline=False, cls='btn-success btn-sm')
BTN_EDITAR_PRODUTO = Button(label='Editar Produto', icon='pencil-square', color='primary', outline=True, cls='btn-outline btn-primary btn-sm')
BTN_ENTRAR = Button(label='Entrar', color='danger', outline=False, cls='btn-danger btn-sm')
BTN_ACESSAR = Button(label='Acessar', color='danger', outline=False, cls='btn-danger btn-sm')


# ── Registro nomeado de ações (Form.buttons / Lista) ──
# Resolução em app.ajsystem.form: um nome resolve para o default abaixo.
# Endpoint e campo booleano são derivados por convenção
# (endpoint = '<blueprint>.toggle', campo default 'ativo').
ACTIONS = {
    'on_off': Button(
        label='Ativar', icon='check',
        label_off='Desativar', icon_off='xmark',
        color='success', outline=True, position='nav_right', on_off=True,
    ),
}


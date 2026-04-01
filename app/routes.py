import os
import bcrypt
import datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, abort, jsonify, Response, session, current_app
from .supabase_client import supabase

bp = Blueprint('main', __name__)

# ------------------------------
# MIDDLEWARES (DECORATORS)
# ------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "tipo" not in session:
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated

def cliente_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("tipo") != "cliente":
            return Response(status=204)
        return f(*args, **kwargs)
    return decorated

def profissional_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("tipo") != "profissional":
            return Response(status=204)
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("tipo") != "admin":
            return Response(status=204)
        return f(*args, **kwargs)
    return decorated

# ------------------------------
# FUNÇÕES AUXILIARES
# ------------------------------

def buscar_cliente_por_email(email):
    resp = supabase.table("clientes").select("*").eq("email", email).execute()
    if resp.data:
        return resp.data[0]
    return None

def buscar_adm(usuario):
    resp = supabase.table("admin").select("*").eq("usuario", usuario).execute()
    if resp.data:
        return resp.data[0]
    return None

def gerar_intervalos(horario_str):
    inicio_str, fim_str = horario_str.split('-')
    inicio_h, inicio_m = map(int, inicio_str.replace('h', '').split(':') if ':' in inicio_str else (inicio_str.replace('h', ''), "00"))
    fim_h, fim_m = map(int, fim_str.replace('h', '').split(':') if ':' in fim_str else (fim_str.replace('h', ''), "00"))
    atual = datetime.datetime(2000, 1, 1, inicio_h, inicio_m)
    fim = datetime.datetime(2000, 1, 1, fim_h, fim_m)
    horarios = []
    while atual < fim:
        horarios.append(atual.strftime("%H:%M"))
        atual += datetime.timedelta(minutes=30)
    return horarios

# ------------------------------
# ROTAS DE PÁGINAS
# ------------------------------

@bp.route('/')
@bp.route('/landing')
def landing():
    return render_template('landing.html')

@bp.route('/app')
@bp.route('/plataforma')
def app_home():
    return render_template('index.html')

@bp.route('/sobre')
def sobre():
    return render_template('inicio-clinica.html')

@bp.route('/agendamentos')
@cliente_required
def agendamentos():
    if "cliente_id" not in session:
        return redirect(url_for('main.login'))
    resp = supabase.table("profissionais").select("*").execute()
    profissionais = resp.data
    return render_template("agendamentos.html", profissionais=profissionais)

@bp.route("/buscar_horarios")
def buscar_horarios():
    data_str = request.args.get("data")
    prof_id = request.args.get("prof")
    if not data_str or not prof_id:
        return jsonify({"horarios": []})
    data_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d")
    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    dia_semana = dias[data_obj.weekday()] 
    resp = supabase.table("horarios_profissionais").select("*").eq("profissional_id", prof_id).eq("dia_semana", dia_semana).execute()
    if not resp.data:
        return jsonify({"horarios": []})
    horario_str = resp.data[0]["horario"]
    horarios_30m = gerar_intervalos(horario_str)
    return jsonify({"horarios": horarios_30m})

@bp.route("/profissionais_disponiveis")
def profissionais_disponiveis():
    data_str = request.args.get("data")
    if not data_str:
        return jsonify({"profissionais": []})
    data_obj = datetime.datetime.strptime(data_str, "%Y-%m-%d")
    dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    dia_semana = dias[data_obj.weekday()]
    resp = supabase.table("horarios_profissionais").select("*").eq("dia_semana", dia_semana).execute()
    profissionais_ids = [h["profissional_id"] for h in resp.data]
    if not profissionais_ids:
        return jsonify({"profissionais": []})
    resp2 = supabase.table("profissionais").select("*").in_("id", profissionais_ids).execute()
    return jsonify({"profissionais": resp2.data})

@bp.route("/confirmar_agendamento", methods=["POST"])
def confirmar_agendamento():
    horario = request.form.get("horario")
    data = request.form.get("data")
    profissional_id = request.form.get("profissional_id")
    cliente_id = session.get("cliente_id")
    if not cliente_id:
        return "Erro: cliente não está logado.", 400
    if not horario or not data or not profissional_id:
        return "Dados inválidos", 400
    try:
        supabase.table("consultas").insert({
            "cliente_id": cliente_id,
            "profissional_id": profissional_id,
            "data": data,
            "horario": horario,
            "status": "pendente"
        }).execute()
        return redirect(url_for("main.consultas_cliente"))
    except Exception as e:
        print("Erro ao agendar:", e)
        return "Erro ao agendar consulta", 500
    
@bp.route('/consultas_cliente')
@cliente_required
def consultas_cliente():
    if "cliente_id" not in session:
        return redirect(url_for('main.login'))
    
    cliente_id = session.get("cliente_id")

    # Buscar dados do cliente
    rc = supabase.table("clientes").select("*").eq("id", cliente_id).execute()
    cliente = rc.data[0] if rc.data else None

    # Buscar consultas com dados do profissional
    rcons = supabase.table("consultas")\
        .select("""
            id,
            data,
            horario,
            status,
            profissionais (
                nome,
                especialidade
            )
        """)\
        .eq("cliente_id", cliente_id)\
        .order("data")\
        .order("horario")\
        .execute()

    return render_template("consultas_marcadas.html",
                           cliente=cliente,
                           consultas=rcons.data)

@bp.route('/cancelar_consulta/<int:id>')
@cliente_required
def cancelar_consulta(id):
    try:
        supabase.table("consultas").delete().eq("id", id).execute()
        return redirect(url_for('main.consultas_cliente'))
    except Exception as e:
        print("Erro ao cancelar consulta:", e)
        return redirect(url_for('main.consultas_cliente'))

@bp.route('/perfil')
def perfil():
    if "cliente_id" not in session:
        return redirect(url_for("main.login"))

    cliente_id = session["cliente_id"]

    resp = supabase.table("clientes").select("*").eq("id", cliente_id).execute()

    if not resp.data:
        return "Cliente não encontrado", 404

    cliente = resp.data[0]

    return render_template("perfil.html", cliente=cliente)


@bp.route('/atualizar_perfil', methods=["POST"])
def atualizar_perfil():
    if "cliente_id" not in session:
        return redirect(url_for("main.login"))

    cliente_id = session["cliente_id"]

    nome = request.form.get("nome")
    data_nascimento = request.form.get("data_nascimento")
    cpf = request.form.get("cpf")
    telefone = request.form.get("telefone")
    email = request.form.get("email")
    endereco = request.form.get("endereco")

    nova_senha = request.form.get("nova_senha")
    confirmar_senha = request.form.get("confirmar_senha")

    update_data = {
        "nome": nome,
        "data_nascimento": data_nascimento,
        "cpf": cpf,
        "telefone": telefone,
        "email": email,
        "endereco": endereco
    }

    if nova_senha:
        if nova_senha != confirmar_senha:
            return "Erro: As senhas não coincidem.", 400

        senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        update_data["senha"] = senha_hash

    supabase.table("clientes").update(update_data).eq("id", cliente_id).execute()

    return redirect(url_for("main.perfil"))

# ------------------------------
# LOGIN E CADASTRO
# ------------------------------

@bp.route('/login')
def login():
    erro = request.args.get('erro')
    return render_template('login-paciente.html', erro=erro)

@bp.route('/processar_login', methods=['POST'])
def processar_login():
    email = request.form.get('email')
    senha = request.form.get('senha')
    cliente = buscar_cliente_por_email(email)
    if not cliente:
        return redirect(url_for('main.login', erro="Usuário não encontrado."))
    if not bcrypt.checkpw(senha.encode('utf-8'), cliente["senha"].encode('utf-8')):
        return redirect(url_for('main.login', erro="Senha incorreta."))
    session.clear()
    session.permanent = True
    session["cliente_id"] = cliente["id"]
    session["tipo"] = "cliente"
    return redirect(url_for('main.agendamentos'))

@bp.route('/cadastro')
def cadastro():
    erro = request.args.get('erro')
    return render_template('cadastro.html', erro=erro)

@bp.route('/processar_cadastro', methods=['POST'])
def processar_cadastro():
    nome = request.form.get('nomeCompleto')
    data_nascimento = request.form.get('dataNascimento')
    cpf = request.form.get('cpf')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    endereco = request.form.get('endereco')
    senha = request.form.get('senha')
    confirmar = request.form.get('confirmarSenha')
    if senha != confirmar:
        return redirect(url_for('main.cadastro', erro="As senhas não coincidem."))
    if buscar_cliente_por_email(email):
        return redirect(url_for('main.cadastro', erro="Este email já está cadastrado."))
    resp_cpf = supabase.table("clientes").select("*").eq("cpf", cpf).execute()
    if resp_cpf.data:
        return redirect(url_for('main.cadastro', erro="Este CPF já está cadastrado."))
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        supabase.table("clientes").insert({
            "nome": nome, "data_nascimento": data_nascimento, "cpf": cpf,
            "telefone": telefone, "email": email, "endereco": endereco, "senha": senha_hash
        }).execute()
        return redirect(url_for('main.login', sucesso="Cadastro realizado com sucesso! Faça login."))
    except Exception as e:
        print("Erro no Supabase:", e)
        return redirect(url_for('main.cadastro', erro="Erro ao cadastrar. Tente novamente."))

# ------------------------------
# PROFISSIONAL
# ------------------------------

@bp.route('/acesso-profissional')
def acesso_profissional():
    erro = request.args.get('erro')
    return render_template('acesso-profissional.html', erro=erro)

@bp.route('/processar_login_profissional', methods=['POST'])
def processar_login_profissional():
    email = request.form.get('emailCorporativo')
    senha = request.form.get('senha')
    pin = request.form.get('pin')
    if not email or not senha or not pin:
        return "Preencha todos os campos.", 400
    resp = supabase.table("profissionais").select("*").eq("email", email).execute()
    if not resp.data:
        return "Profissional não encontrado.", 404
    profissional = resp.data[0]
    senha_hash = profissional.get("senha")
    if not senha_hash or not bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8")):
        return "Senha incorreta.", 401
    if pin != profissional.get("pin"):
        return "PIN incorreto.", 401
    session.clear()
    session.permanent = True
    session["profissional_id"] = profissional["id"]
    session["profissional_nome"] = profissional["nome"]
    session["tipo"] = "profissional"
    return redirect(url_for('main.configurar_horarios'))

@bp.route('/configurar_horarios')
@profissional_required
def configurar_horarios():
    prof_id = session["profissional_id"]
    resp = supabase.table("profissionais").select("*").eq("id", prof_id).execute()
    profissional = resp.data[0] if resp.data else None
    return render_template("configurar_horarios.html", profissional=profissional)

@bp.route('/salvar_horarios', methods=["POST"])
@profissional_required
def salvar_horarios():
    prof_id = session["profissional_id"]
    payload = request.get_json(silent=True)
    if not payload or "horarios" not in payload:
        return jsonify({"error": "dados inválidos"}), 400
    horarios = payload["horarios"]
    try:
        supabase.table("horarios_profissionais").delete().eq("profissional_id", prof_id).execute()
        inserts = [{"profissional_id": prof_id, "dia_semana": h["dia_semana"], "horario": f"{h['inicio']}-{h['fim']}"} for h in horarios]
        if inserts:
            supabase.table("horarios_profissionais").insert(inserts).execute()
        return jsonify({"ok": True})
    except Exception as e:
        print("Erro salvar_horarios:", e)
        return jsonify({"error": "erro interno"}), 500

@bp.route('/consultas_profissional')
@profissional_required
def consultas_profissional():
    if "profissional_id" not in session:
        return redirect(url_for("main.acesso_profissional"))

    prof_id = session["profissional_id"]

    # Buscar dados do profissional
    rp = supabase.table("profissionais").select("*").eq("id", prof_id).execute()
    profissional = rp.data[0]

    # Buscar consultas para esse profissional
    rc = supabase.table("consultas")\
        .select("""
            id,
            data,
            horario,
            status,
            clientes (
                nome,
                email
            )
        """)\
        .eq("profissional_id", prof_id)\
        .order("data")\
        .order("horario")\
        .execute()

    consultas = rc.data

    return render_template("consultas_profissional.html",
                           profissional=profissional,
                           consultas=consultas)

@bp.route('/cancelar_consulta_prof/<int:id>')
@profissional_required
def cancelar_consulta_prof(id):
    # Segurança: confirmar que a consulta pertence ao cliente
    if "profissional_id" not in session:
        return redirect(url_for("acesso_profissional"))

    prof_id = session["profissional_id"]

    resp = supabase.table("consultas").select("*").eq("id", id).execute()

    if not resp.data:
        return "Consulta não encontrada", 404

    consulta = resp.data[0]

    if consulta["profissional_id"] != prof_id:
        return "Acesso negado", 401

    supabase.table("consultas").delete().eq("id", id).execute()

    return redirect(url_for("main.consultas_profissional"))

@bp.route('/horarios_profissional')
def horarios_profissional():
    """
    Retorna JSON com horários do profissional logado.
    Se query param 'prof' for passado e o usuário for admin (ou for o próprio prof), permite buscar outro.
    """
    # permitir leitura do próprio profissional mesmo sem param
    prof_param = request.args.get("prof")
    prof_id = None

    if prof_param:
        # se passou prof, permitir só se for admin_token correto
        token = request.args.get("admin_token")
        if token == current_app.config['ADMIN_TOKEN']:
            prof_id = prof_param
        else:
            # não autorizado a consultar outro profissional
            return jsonify({"horarios": []})
    else:
        if "profissional_id" not in session:
            return jsonify({"horarios": []})
        prof_id = session["profissional_id"]

    resp = supabase.table("horarios_profissionais")\
        .select("*")\
        .eq("profissional_id", prof_id)\
        .execute()

    horarios = resp.data if resp.data else []
    # padronizar saída
    out = [{"id": r.get("id"), "dia_semana": r.get("dia_semana"), "horario": r.get("horario")} for r in horarios]

    return jsonify({"horarios": out})


# ------------------------------
# ADMIN
# ------------------------------

@bp.route('/login_adm')
def login_adm():
    if session.get("admin_authed"):
        return redirect(url_for('main.admin_profissionais'))
    erro = request.args.get("erro")
    return render_template('login-adm.html', erro=erro)

@bp.route('/processar_login_adm', methods=["POST"])
def processar_login_adm():
    usuario = request.form.get('usuario')
    senha = request.form.get('senha')
    admin = buscar_adm(usuario)
    if not admin or not bcrypt.checkpw(senha.encode('utf-8'), admin["senha"].encode('utf-8')):
        return redirect(url_for('main.login_adm', erro="Usuário ou senha inválidos."))
    session.clear()
    session.permanent = True
    session["tipo"] = "admin"
    session["admin_authed"] = True
    return redirect(url_for('main.admin_profissionais'))

@bp.route('/admin_profissionais')
@admin_required
def admin_profissionais():
    if not session.get("admin_authed"):
        return redirect(url_for("main.login_adm", erro="Faça login para acessar o painel."))
    resp = supabase.table("profissionais").select("*").execute()
    return render_template("admin_profissionais.html", profissionais=resp.data)

@bp.route('/admin_criar_profissional', methods=["POST"])
@admin_required
def admin_criar_profissional():
    nome = request.form.get("nome")
    especialidade = request.form.get("especialidade")
    email = request.form.get("email")
    senha = request.form.get("senha")
    pin = request.form.get("pin")
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        supabase.table("profissionais").insert({
            "nome": nome,
            "especialidade": especialidade,
            "email": email,
            "senha": senha_hash,
            "pin": pin
        }).execute()
        return redirect(url_for('main.admin_profissionais'))
    except Exception as e:
        print("Erro no Supabase:", e)
        return redirect(url_for('main.admin_profissionais', erro="Erro ao cadastrar."))
    
@bp.route('/admin_deletar_profissional/<int:id>', methods=["POST"])
@admin_required
def admin_deletar_profissional(id):
    try:
        supabase.table("profissionais").delete().eq("id", id).execute()
        return redirect(url_for('main.admin_profissionais'))
    except Exception as e:
        print("Erro ao deletar profissional:", e)
        return redirect(url_for('main.admin_profissionais', erro="Erro ao deletar profissional."))

# ------------------------------
# TRATATIVAS GET PARA POST
# ------------------------------

@bp.route("/confirmar_agendamento", methods=["GET"])
def confirmar_agendamento_get(): return redirect(url_for("main.consultas_cliente"))

@bp.route("/processar_login", methods=["GET"])
def processar_login_get(): return redirect(url_for("main.login"))

@bp.app_errorhandler(404)
def page_not_found(e):
    return redirect(url_for("main.landing"))

import streamlit as st
import sqlite3
import os
import re
import time
from datetime import datetime
from fpdf import FPDF
import extra_streamlit_components as stx

# Configuração da página
st.set_page_config(page_title="PCD Online - UFF", page_icon="📁", layout="wide")

# Estilização CSS para um visual acadêmico e profissional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #1a3a5a; font-family: 'Segoe UI', sans-serif; }
    .stButton>button { background-color: #1a3a5a; color: white; border-radius: 5px; font-weight: bold; height: 40px; width: 100%; }
    .stButton>button:hover { background-color: #2c527a; border: 1px solid #1a3a5a; }
    .report-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #1a3a5a; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- GERENCIADOR DE COOKIES / LOCAL STORAGE ---
cookie_manager = stx.CookieManager(key="cookie_manager_global")

# Sincronização do iframe com o navegador
time.sleep(0.2)

# --- BANCO DE DADOS PERSISTENTE LOCAL ---
DB_PATH = "pcd_data_permanente.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (matricula TEXT PRIMARY KEY, nome TEXT NOT NULL, orgao TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS membros_grupo (id INTEGER PRIMARY KEY AUTOINCREMENT, matricula_lider TEXT, nome_membro TEXT, matricula_membro TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS estrutura (id INTEGER PRIMARY KEY AUTOINCREMENT, matricula TEXT, tipo TEXT NOT NULL, codigo TEXT NOT NULL, texto TEXT NOT NULL, UNIQUE(matricula, codigo), FOREIGN KEY (matricula) REFERENCES alunos(matricula))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin_config (usuario TEXT PRIMARY KEY, senha TEXT NOT NULL)''')
    
    # Credenciais atualizadas: admin0 / 0admin
    cursor.execute("INSERT OR IGNORE INTO admin_config VALUES ('admin0', '0admin')")
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- TENTATIVA DE LOGIN AUTOMÁTICO VIA COOKIE ---
if 'aluno_logado' not in st.session_state:
    try:
        matricula_salva = cookie_manager.get(cookie="uff_pcd_matricula")
        if matricula_salva:
            cursor.execute("SELECT nome, orgao FROM alunos WHERE matricula = ?", (str(matricula_salva).strip(),))
            aluno_recuperado = cursor.fetchone()
            if aluno_recuperado:
                st.session_state.update({
                    'aluno_matricula': str(matricula_salva).strip(),
                    'aluno_nome': aluno_recuperado[0],
                    'aluno_orgao': aluno_recuperado[1],
                    'aluno_logado': True
                })
    except Exception:
        pass

# --- CHAVE MESTRA DE RECUPERAÇÃO ---
CHAVE_MESTRA_RECUPERACAO = "UFF#Admin#Seguro#2026"

# --- CONTROLE ANTI-SPAM ---
if 'last_submit_time' not in st.session_state:
    st.session_state['last_submit_time'] = 0.0
if 'last_submit_text' not in st.session_state:
    st.session_state['last_submit_text'] = ""

# --- FUNÇÕES DE AUXÍLIO E GERAÇÃO DE CÓDIGOS AUTOMÁTICOS ---
def obter_proximo_codigo(matricula, tipo, pai_codigo=None):
    if tipo == "Função":
        cursor.execute("SELECT codigo FROM estrutura WHERE matricula = ? AND tipo = 'Função'", (matricula,))
        codigos = []
        for x in cursor.fetchall():
            c_limpo = x[0].replace('.', '').strip()
            if c_limpo.isdigit():
                codigos.append(int(c_limpo))
        proximo = max(codigos) + 1 if codigos else 1
        return f"{proximo:02d}."
        
    elif tipo == "Subfunção" and pai_codigo:
        pai_limpo = pai_codigo.rstrip('.')
        cursor.execute("SELECT codigo FROM estrutura WHERE matricula = ? AND tipo = 'Subfunção' AND codigo LIKE ?", 
                       (matricula, f"{pai_limpo}.%"))
        sufixos = []
        for row in cursor.fetchall():
            partes = row[0].rstrip('.').split('.')
            if len(partes) >= 2:
                try: sufixos.append(int(partes[1]))
                except ValueError: pass
        proximo = max(sufixos) + 1 if sufixos else 1
        return f"{pai_limpo}.{proximo:02d}."
        
    elif tipo == "Atividade" and pai_codigo:
        pai_limpo = pai_codigo.rstrip('.')
        cursor.execute("SELECT codigo FROM estrutura WHERE matricula = ? AND tipo = 'Atividade' AND codigo LIKE ?", 
                       (matricula, f"{pai_limpo}.%"))
        sufixos = []
        for row in cursor.fetchall():
            partes = row[0].rstrip('.').split('.')
            if len(partes) >= 3:
                try: sufixos.append(int(partes[2]))
                except ValueError: pass
        proximo = max(sufixos) + 1 if sufixos else 1
        return f"{pai_limpo}.{proximo:02d}."
        
    elif tipo == "Tipo documental" and pai_codigo:
        pai_limpo = pai_codigo.rstrip('.')
        cursor.execute("SELECT codigo FROM estrutura WHERE matricula = ? AND tipo = 'Tipo documental' AND codigo LIKE ?", 
                       (matricula, f"{pai_limpo}.%"))
        sufixos = []
        for row in cursor.fetchall():
            partes = row[0].rstrip('.').split('.')
            if len(partes) >= 4:
                try: sufixos.append(int(partes[3]))
                except ValueError: pass
        proximo = max(sufixos) + 1 if sufixos else 1
        return f"{pai_limpo}.{proximo:02d}."
    return ""

class CustomPCDPDF(FPDF):
    def __init__(self, orgao, emitente, membros):
        super().__init__()
        self.orgao = orgao
        self.emitente = emitente
        self.membros = membros
        self.data_emissao = datetime.now().strftime("%d/%m/%Y %H:%M")

    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, self.encode_txt('UNIVERSIDADE FEDERAL FLUMINENSE'), 0, 1, 'C')
        self.cell(0, 5, self.encode_txt('INSTITUTO DE ARTE E COMUNICAÇÃO SOCIAL'), 0, 1, 'C')
        self.cell(0, 5, self.encode_txt('DEPARTAMENTO DE CIÊNCIA DA INFORMAÇÃO'), 0, 1, 'C')
        self.cell(0, 5, self.encode_txt('CURSO DE GRADUAÇÃO EM ARQUIVOLOGIA'), 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, self.encode_txt('DISCIPLINA DE TÓPICOS ESPECIAIS 1'), 0, 1, 'C')
        self.cell(0, 5, self.encode_txt('PROFESSORES: CLARISSA SCHMIDT E PAULO ALENCAR'), 0, 1, 'C')
        self.ln(10)
        self.line(10, 42, 200, 42)

    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.line(10, 275, 200, 275)
        self.cell(0, 10, self.encode_txt(f'Emitido por: {self.emitente} | Data: {self.data_emissao}'), 0, 0, 'L')
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'R')

    def encode_txt(self, texto):
        if not texto: return ""
        # Remove travessões complexos e força decodificação segura compatível com o PDF Arial Standard
        texto_limpo = str(texto).replace('–', '-').replace('—', '-')
        return texto_limpo.encode('latin-1', 'ignore').decode('latin-1')

def ordenar_codigos_arquivisticos(item):
    partes = re.findall(r'\d+', item[1])
    return [int(p) for p in partes]

def gerar_relatorio_final(orgao, emitente, matricula, membros, dados):
    pdf = CustomPCDPDF(orgao, emitente, membros)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 15, pdf.encode_txt("PLANO DE CLASSIFICAÇÃO DE DOCUMENTOS"), 0, 1, 'C')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, pdf.encode_txt(f"ÓRGÃO PRODUTOR: {orgao.upper()}"), 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(230, 235, 240)
    pdf.cell(0, 8, pdf.encode_txt(" COMPONENTES DO GRUPO"), 0, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, pdf.encode_txt(f"Líder / Responsável: {emitente} ({matricula})"), 0, 1, 'L')
    for m_nome, m_mat in membros:
        pdf.cell(0, 6, pdf.encode_txt(f"Integrante: {m_nome} ({m_mat})"), 0, 1, 'L')
    pdf.ln(8)

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, pdf.encode_txt(" ESTRUTURA ARQUIVÍSTICA DO PLANO"), 0, 1, 'L', fill=True)
    pdf.ln(4)
    
    dados_ordenados = sorted(dados, key=ordenar_codigos_arquivisticos)
    
    for _, cod, tipo, txt in dados_ordenados:
        cod_exibicao = cod if cod.endswith('.') else f"{cod}."
        
        if pdf.get_y() > 245: 
            pdf.add_page()

        if tipo == "Função":
            pdf.set_font('Arial', 'B', 11)
            pdf.set_fill_color(200, 215, 230)
            pdf.set_text_color(26, 58, 90)
            pdf.set_x(10)
            pdf.cell(0, 7, pdf.encode_txt(f"{cod_exibicao} {txt}"), 0, 1, 'L', fill=True)
            pdf.ln(2)
            continue
        elif tipo == "Subfunção":
            recuo, largura, tam_fonte, estilo = 16, 174, 10, 'B'
            pdf.set_text_color(50, 50, 50)
        elif tipo == "Atividade":
            recuo, largura, tam_fonte, estilo = 24, 166, 10, ''
            pdf.set_text_color(80, 80, 80)
        else:
            recuo, largura, tam_fonte, estilo = 32, 158, 9.5, 'I'
            pdf.set_text_color(110, 110, 110)
        
        pdf.set_font('Arial', estilo, tam_fonte)
        pdf.set_x(recuo)
        pdf.multi_cell(largura, 6, pdf.encode_txt(f"{cod_exibicao} {txt}"))
        pdf.ln(1)
        
    pdf.set_text_color(0, 0, 0)
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACE PRINCIPAL ---
st.title("Plano de Classificação Online - UFF")
menu = st.sidebar.radio("Navegação", ["Área do Aluno", "Área do Professor (Admin)"])

if menu == "Área do Aluno":
    st.header("📝 Acesso do Estudante")
    
    if 'aluno_logado' not in st.session_state:
        opcao_acesso = st.radio("Selecione o modo de entrada:", ["Já Estou Cadastrado", "Primeiro Acesso (Criar Novo Perfil)"], horizontal=True)
        st.write("---")
        matricula_input = st.text_input("Digite sua Matrícula:").strip()
        nome_input = st.text_input("Digite seu Nome Completo:").strip()
        
        orgao_input = ""
        if opcao_acesso == "Primeiro Acesso (Criar Novo Perfil)":
            orgao_input = st.text_input("Nome da Instituição / Órgão do seu plano:").strip()
        
        if st.button("🚀 Entrar / Confirmar Cadastro no Sistema"):
            if not matricula_input or not nome_input:
                st.error("Por favor, preencha a Matrícula e o Nome Completo.")
            else:
                cursor.execute("SELECT nome, orgao FROM alunos WHERE matricula = ?", (matricula_input,))
                aluno_existente = cursor.fetchone()
                
                if opcao_acesso == "Já Estou Cadastrado":
                    if aluno_existente:
                        try:
                            cookie_manager.set(cookie="uff_pcd_matricula", value=matricula_input, max_age=2592000, key="set_cookie_login_final")
                        except Exception:
                            pass
                        st.session_state.update({'aluno_matricula': matricula_input, 'aluno_nome': aluno_existente[0], 'aluno_orgao': aluno_existente[1], 'aluno_logado': True})
                        st.success("Sucesso! Carregando dados...")
                        st.rerun()
                    else:
                        st.error("Matrícula não localizada. Mude para 'Primeiro Acesso' se for a primeira vez.")
                else:
                    if not orgao_input:
                        st.error("Para novos cadastros, preencha o nome do Órgão.")
                    elif aluno_existente:
                        st.warning("Esta matrícula já existe. Use a opção 'Já Estou Cadastrado'.")
                    else:
                        cursor.execute("INSERT INTO alunos VALUES (?, ?, ?)", (matricula_input, nome_input, orgao_input))
                        conn.commit()
                        try:
                            cookie_manager.set(cookie="uff_pcd_matricula", value=matricula_input, max_age=2592000, key="set_cookie_cadastro_final")
                        except Exception:
                            pass
                        st.session_state.update({'aluno_matricula': matricula_input, 'aluno_nome': nome_input, 'aluno_orgao': orgao_input, 'aluno_logado': True})
                        st.success("Perfil gerado com sucesso!")
                        st.rerun()
                        
    else:
        st.info(f"Estudante Responsável: **{st.session_state['aluno_nome']}** | Matrícula: **{st.session_state['aluno_matricula']}** | Órgão: **{st.session_state['aluno_orgao']}**")
        if st.sidebar.button("🚪 Sair / Mudar de Conta"):
            try:
                cookie_manager.delete(cookie="uff_pcd_matricula", key="delete_cookie_logout_final")
            except Exception:
                pass
            del st.session_state['aluno_logado']
            st.rerun()
            
        st.write("---")
        st.header("📁 Gerenciamento do seu Plano de Classificação")
        
        tab1, tab2, tab3, tab4 = st.tabs(["👥 Integrantes do Grupo", "➕ Inserir Novos Elementos", "🔍 Visualizar & Editar Estrutura", "📄 Exportar em PDF"])
        
        with tab1:
            st.subheader("Componentes do Grupo de Trabalho")
            with st.form("form_membros", clear_on_submit=True):
                col_m_nome = st.text_input("Nome do Integrante:")
                col_m_mat = st.text_input("Matrícula do Integrante:")
                if st.form_submit_button("➕ Vincular Membro ao Grupo"):
                    if col_m_nome and col_m_mat:
                        cursor.execute("INSERT INTO membros_grupo (matricula_lider, nome_membro, matricula_membro) VALUES (?, ?, ?)", 
                                       (st.session_state['aluno_matricula'], col_m_nome.strip(), col_m_mat.strip()))
                        conn.commit()
                        st.success(f"{col_m_nome} adicionado!")
                        st.rerun()
            
            cursor.execute("SELECT id, nome_membro, matricula_membro FROM membros_grupo WHERE matricula_lider = ?", (st.session_state['aluno_matricula'],))
            membros_atuais = cursor.fetchall()
            if membros_atuais:
                for mid, mnome, mmat in membros_atuais:
                    col_list, col_btn = st.columns([6, 1])
                    col_list.write(f"• **{mnome}** ({mmat})")
                    if col_btn.button("🗑️", key=f"del_m_{mid}"):
                        cursor.execute("DELETE FROM membros_grupo WHERE id = ?", (mid,))
                        conn.commit()
                        st.rerun()

        with tab2:
            st.subheader("Cadastrar Item na Árvore Hierárquica")
            tipo_item = st.selectbox("Nível Hierárquico a cadastrar:", ["Função", "Subfunção", "Atividade", "Tipo documental"])
            mat_atual = st.session_state['aluno_matricula']
            
            codigo_sugerido = ""
            pai_info = ""
            
            if tipo_item == "Função":
                codigo_sugerido = obter_proximo_codigo(mat_atual, "Função")
                st.info(f"Código Automático Gerado: **{codigo_sugerido}**")
                
            elif tipo_item == "Subfunção":
                cursor.execute("SELECT codigo, texto FROM estrutura WHERE matricula = ? AND tipo = 'Função'", (mat_atual,))
                funcoes = cursor.fetchall()
                if funcoes:
                    pai = st.selectbox("Selecione a Função Pai:", funcoes, format_func=lambda x: f"{x[0]} {x[1]}")
                    codigo_sugerido = obter_proximo_codigo(mat_atual, "Subfunção", pai[0])
                    pai_info = f"Função {pai[0]} ({pai[1]})"
                    st.info(f"Código Estrutural Gerado: **{codigo_sugerido}**")
                else:
                    st.warning("Adicione uma Função antes de criar uma Subfunção.")
                    
            elif tipo_item == "Atividade":
                cursor.execute("SELECT codigo, texto FROM estrutura WHERE matricula = ? AND tipo = 'Subfunção'", (mat_atual,))
                subfuncoes = cursor.fetchall()
                if subfuncoes:
                    pai = st.selectbox("Selecione a Subfunção Pai:", subfuncoes, format_func=lambda x: f"{x[0]} {x[1]}")
                    codigo_sugerido = obter_proximo_codigo(mat_atual, "Atividade", pai[0])
                    pai_info = f"Subfunção {pai[0]} ({pai[1]})"
                    st.info(f"Código Estrutural Gerado: **{codigo_sugerido}**")
                else:
                    st.warning("Adicione uma Subfunção antes de criar uma Atividade.")
                    
            elif tipo_item == "Tipo documental":
                cursor.execute("SELECT codigo, texto FROM estrutura WHERE matricula = ? AND tipo = 'Atividade'", (mat_atual,))
                atividades = cursor.fetchall()
                if atividades:
                    pai = st.selectbox("Selecione a Atividade Pai:", atividades, format_func=lambda x: f"{x[0]} {x[1]}")
                    codigo_sugerido = obter_proximo_codigo(mat_atual, "Tipo documental", pai[0])
                    pai_info = f"Atividade {pai[0]} ({pai[1]})"
                    st.info(f"Código Estrutural Gerado: **{codigo_sugerido}**")
                else:
                    st.warning("Adicione uma Atividade antes de criar um Tipo Documental.")

            texto_item = st.text_area("Descrição/Texto do Item:", max_chars=250)
            
            if codigo_sugerido and texto_item.strip():
                with st.popover(f"💾 Gravar {tipo_item}"):
                    st.warning("⚠️ Confirma a vinculação estrutural deste item?")
                    if pai_info:
                        st.write(f"📌 **Vinculado diretamente a:** `{pai_info}`")
                    st.write(f"🔢 **Código gerado:** {codigo_sugerido}")
                    st.write(f"📝 **Descrição:** {texto_item.strip()}")
                    
                    if st.button("Sim, Confirmar e Salvar", key=f"btn_confirmar_{tipo_item}"):
                        agora = time.time()
                        tempo_decorrido = agora - st.session_state['last_submit_time']
                        texto_limpo = texto_item.strip()
                        
                        if tempo_decorrido < 3.0 and texto_limpo == st.session_state['last_submit_text']:
                            st.error("⛔ Item repetido detectado! Aguarde 3 segundos.")
                        else:
                            st.session_state['last_submit_time'] = agora
                            st.session_state['last_submit_text'] = texto_limpo
                            
                            try:
                                cursor.execute("INSERT INTO estrutura (matricula, tipo, codigo, texto) VALUES (?, ?, ?, ?)", 
                                               (mat_atual, tipo_item, codigo_sugerido, texto_limpo))
                                conn.commit()
                                st.success(f"{tipo_item} gravado com sucesso!")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Erro: Este código já existe nesta conta.")
            else:
                st.caption("Preencha o campo de texto para habilitar o salvamento.")

        with tab3:
            st.subheader(f"Estrutura Atual")
            cursor.execute("SELECT id, codigo, tipo, texto FROM estrutura WHERE matricula = ?", (mat_atual,))
            dados = cursor.fetchall()
            
            if dados:
                dados_ordenados = sorted(dados, key=ordenar_codigos_arquivisticos)
                for item_id, cod, tipo, txt in dados_ordenados:
                    cod_exibicao = cod if cod.endswith('.') else f"{cod}."
                    if tipo == "Função": st.markdown(f"**{cod_exibicao} {txt}**")
                    elif tipo == "Subfunção": st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📄 {cod_exibicao} {txt}")
                    elif tipo == "Atividade": st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔹 {cod_exibicao} {txt}")
                    elif tipo == "Tipo documental": st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔸 *{cod_exibicao} {txt}*")
                
                st.write("---")
                st.subheader("🛠️ Painel de Modificações Rápidas")
                for item_id, cod, tipo, txt in dados_ordenados:
                    col_info, col_edit, col_del = st.columns([6, 2, 1])
                    col_info.write(f"`{cod}` **[{tipo}]** — {txt}")
                    with col_edit:
                        with st.expander("✏️ Editar"):
                            novo_texto = st.text_input("Alterar texto:", value=txt, key=f"txt_al_{item_id}")
                            if st.button("Confirmar", key=f"btn_edit_al_{item_id}"):
                                cursor.execute("UPDATE estrutura SET texto = ? WHERE id = ?", (novo_texto.strip(), item_id))
                                conn.commit()
                                st.rerun()
                    if col_del.button("🗑️", key=f"btn_del_al_{item_id}"):
                        cursor.execute("DELETE FROM estrutura WHERE id = ?", (item_id,))
                        conn.commit()
                        st.rerun()

        with tab4:
            st.subheader("📥 Exportação Oficial em PDF")
            cursor.execute("SELECT id, codigo, tipo, texto FROM estrutura WHERE matricula = ?", (mat_atual,))
            dados_reais = cursor.fetchall()
            cursor.execute("SELECT nome_membro, matricula_membro FROM membros_grupo WHERE matricula_lider = ?", (mat_atual,))
            membros_lista = cursor.fetchall()
            
            if dados_reais:
                try:
                    pdf_data = gerar_relatorio_final(st.session_state['aluno_orgao'], st.session_state['aluno_nome'], st.session_state['aluno_matricula'], membros_lista, dados_reais)
                    st.download_button(label="📄 Baixar Relatório UFF", data=pdf_data, file_name=f"Plano_Classificacao_{st.session_state['aluno_orgao']}.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Erro ao compilar o PDF: {e}")

elif menu == "Área do Professor (Admin)":
    st.header("🔒 Painel Administrativo do Professor")
    
    if 'admin_logado' not in st.session_state:
        usuario = st.text_input("Usuário Admin:").strip()
        senha = st.text_input("Senha Admin:", type="password").strip()
        
        col_btn_log, col_btn_esqueci = st.columns([2, 2])
        
        with col_btn_log:
            if st.button("Acessar Painel"):
                cursor.execute("SELECT senha FROM admin_config WHERE usuario = ?", (usuario,))
                res = cursor.fetchone()
                if res and res[0] == senha:
                    st.session_state['admin_logado'] = True
                    st.success("Acesso autorizado!")
                    st.rerun()
                else:
                    st.error("Credenciais inválidas.")
                    
        with col_btn_esqueci:
            with st.popover("Recuperar Senha"):
                st.subheader("🔑 Recuperação via Chave Mestra")
                input_chave_mestra = st.text_input("Chave Mestra de Segurança:", type="password", key="input_master_key")
                nova_senha_emergencia = st.text_input("Defina sua Nova Senha do Painel:", type="password", key="input_new_pass_emergency")
                
                if st.button("Confirmar Alteração"):
                    if input_chave_mestra == CHAVE_MESTRA_RECUPERACAO:
                        if not nova_senha_emergencia.strip():
                            st.error("A nova senha não pode estar em branco.")
                        else:
                            cursor.execute("UPDATE admin_config SET senha = ? WHERE usuario = 'admin0'", (nova_senha_emergencia.strip(),))
                            conn.commit()
                            st.success("✅ Autenticado! Senha redefinida.")
                            st.rerun()
                    else:
                        st.error("❌ Chave Mestra inválida.")

    else:
        if st.sidebar.button("🚪 Sair do Painel Admin"):
            del st.session_state['admin_logado']
            st.rerun()
            
        tab_prof1, tab_prof2, tab_prof3 = st.tabs(["📚 Alunos Cadastrados", "🚨 Ferramenta de Recuperação", "🔒 Configurações"])
        
        with tab_prof1:
            cursor.execute("SELECT matricula, nome, orgao FROM alunos")
            lista_alunos = cursor.fetchall()
            
            if lista_alunos:
                for al_mat, al_nome, al_org in lista_alunos:
                    cursor.execute("SELECT nome_membro, matricula_membro FROM membros_grupo WHERE matricula_lider = ?", (al_mat,))
                    membros_al = cursor.fetchall()
                    texto_membros = ", ".join([f"{n} ({m})" for n, m in membros_al]) if membros_al else "Apenas o líder"
                    
                    with st.expander(f"👤 Grupo de {al_nome} — Órgão: {al_org} ({texto_membros})"):
                        if st.checkbox("Habilitar exclusão permanente", key=f"chk_total_{al_mat}"):
                            if st.button(f"🔥 Apagar Grupo de {al_nome}", key=f"btn_total_{al_mat}"):
                                cursor.execute("DELETE FROM estrutura WHERE matricula = ?", (al_mat,))
                                cursor.execute("DELETE FROM membros_grupo WHERE matricula_lider = ?", (al_mat,))
                                cursor.execute("DELETE FROM alunos WHERE matricula = ?", (al_mat,))
                                conn.commit()
                                st.rerun()
                                
                        st.write("---")
                        cursor.execute("SELECT id, codigo, tipo, texto FROM estrutura WHERE matricula = ?", (al_mat,))
                        itens_aluno = cursor.fetchall()
                        
                        if itens_aluno:
                            itens_ordenados = sorted(itens_aluno, key=ordenar_codigos_arquivisticos)
                            for item_id, cod, tipo, txt in itens_ordenados:
                                col_dados, col_prof_edit, col_prof_del = st.columns([5, 3, 1])
                                col_dados.write(f"**{cod}** `[{tipo}]` — {txt}")
                                with col_prof_edit:
                                    with st.popover("Corrigir"):
                                        txt_professor = st.text_input("Alterar descrição:", value=txt, key=f"prof_in_{item_id}")
                                        if st.button("Salvar", key=f"prof_btn_sav_{item_id}"):
                                            cursor.execute("UPDATE estrutura SET texto = ? WHERE id = ?", (txt_professor.strip(), item_id))
                                            conn.commit()
                                            st.rerun()
                                if col_prof_del.button("🗑️", key=f"prof_del_it_{item_id}"):
                                    cursor.execute("DELETE FROM estrutura WHERE id = ?", (item_id,))
                                    conn.commit()
                                    st.rerun()
            else:
                st.info("Nenhum plano ou aluno cadastrado até o momento.")
                
        with tab_prof3:
            st.subheader("Alterar Senha do Administrador")
            with st.form("form_senha_admin", clear_on_submit=True):
                nova_senha_def = st.text_input("Digite a Nova Senha Forte:", type="password")
                confirma_senha_def = st.text_input("Confirme a Nova Senha Forte:", type="password")
                
                if st.form_submit_button("🔒 Salvar Nova Senha"):
                    if not nova_senha_def.strip():
                        st.error("A senha não pode estar em branco.")
                    elif nova_senha_def != confirma_senha_def:
                        st.error("As senhas inseridas não coincidem.")
                    else:
                        cursor.execute("UPDATE admin_config SET senha = ? WHERE usuario = 'admin0'", (nova_senha_def.strip(),))
                        conn.commit()
                        st.success("Senha alterada com sucesso!")

        with tab_prof2:
            st.subheader("⚡ Painel de Restauração de Emergência")
            st.markdown("""
            Esta ferramenta serve como uma **Planilha-Mãe temporária embutida**. Se o servidor sofrer um reset geral e a estrutura de dados sumir,
            você pode reinjetar instantaneamente uma base completa para testes ou recuperação dos alunos de forma imediata.
            """)
            
            with st.form("form_recuperacao_manual"):
                mat_recup = st.text_input("Matrícula do Líder do Aluno a recuperar:")
                nome_recup = st.text_input("Nome Completo do Líder:")
                orgao_recup = st.text_input("Nome do Órgão Produtor:")
                
                st.write("---")
                st.caption("Aperte o botão abaixo para injetar o perfil do aluno e a estrutura padrão de PCD (Funções e Subfunções acadêmicas) de forma automática.")
                
                if st.form_submit_button("🔥 Executar: Reinserir dados temporários"):
                    if not mat_recup or not nome_recup or not orgao_recup:
                        st.error("Preencha todos os campos do aluno para restaurar.")
                    else:
                        cursor.execute("INSERT OR IGNORE INTO alunos VALUES (?, ?, ?)", (mat_recup.strip(), nome_recup.strip(), orgao_recup.strip()))
                        
                        dados_backup_padrao = [
                            ("Função", "01.", "GESTÃO ACADÊMICA"),
                            ("Subfunção", "01.01.", "Matrícula e Ingresso de Alunos"),
                            ("Atividade", "01.01.01.", "Inscrição em disciplinas de graduação"),
                            ("Tipo documental", "01.01.01.01.", "Requerimento de inscrição"),
                            ("Função", "02.", "ADMINISTRAÇÃO E RECURSOS"),
                            ("Subfunção", "02.01.", "Gerenciamento de Recursos Humanos")
                        ]
                        
                        sucesso_itens = 0
                        for tipo, cod, txt in dados_backup_padrao:
                            try:
                                cursor.execute("INSERT OR IGNORE INTO estrutura (matricula, tipo, codigo, texto) VALUES (?, ?, ?, ?)",
                                               (mat_recup.strip(), tipo, cod, txt))
                                sucesso_itens += 1
                            except Exception:
                                pass
                                
                        conn.commit()
                        st.success(f"🎉 Pronto! O perfil de {nome_recup} foi reativado e {sucesso_itens} itens estruturais foram reinseridos na base local com sucesso!")

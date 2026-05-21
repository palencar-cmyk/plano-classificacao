import streamlit as st
import sqlite3
import os
import re
from datetime import datetime
from fpdf import FPDF

# Configuração da página
st.set_page_config(page_title="PCD Online - UFF", page_icon="📁", layout="wide")

# Estilização CSS para um visual acadêmico e profissional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #1a3a5a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { background-color: #1a3a5a; color: white; border-radius: 5px; font-weight: bold; height: 40px; width: 100%; }
    .stButton>button:hover { background-color: #2c527a; border: 1px solid #1a3a5a; }
    .report-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid #1a3a5a; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS PERSISTENTE ---
DB_PATH = "/data/pcd_data_permanente.db" if os.path.exists("/data") else "pcd_data_permanente.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS alunos (matricula TEXT PRIMARY KEY, nome TEXT NOT NULL, orgao TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS membros_grupo (id INTEGER PRIMARY KEY AUTOINCREMENT, matricula_lider TEXT, nome_membro TEXT, matricula_membro TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS estrutura (id INTEGER PRIMARY KEY AUTOINCREMENT, matricula TEXT, tipo TEXT NOT NULL, codigo TEXT NOT NULL, texto TEXT NOT NULL, FOREIGN KEY (matricula) REFERENCES alunos(matricula))''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- FUNÇÕES DE VALIDAÇÃO E BUSCA ---
def validar_codigo(codigo, tipo):
    codigo = codigo.strip()
    if tipo == "Função":
        return bool(re.match(r"^\d{2}\.?$", codigo)), "Formato ideal: XX (ex: 01)"
    elif tipo == "Subfunção":
        return bool(re.match(r"^\d{2}\.\d{2}\.?$", codigo)), "Formato ideal: XX.XX. (ex: 01.01.)"
    elif tipo == "Atividade":
        return bool(re.match(r"^\d{2}\.\d{2}\.\d{2}\.?$", codigo)), "Formato ideal: XX.XX.XX. (ex: 01.01.01.)"
    elif tipo == "Tipo documental":
        return bool(re.match(r"^\d{2}\.\d{2}\.\d.2\.\d{2}\.?$", codigo)), "Formato ideal: XX.XX.XX.XX. (ex: 01.01.01.01.)"
    return False, ""

def buscar_nome_elemento(matricula, codigo_prefixo):
    if not matricula:
        return "Elemento Pai"
    cod_limpo = codigo_prefixo.strip()
    if cod_limpo.endswith('.'):
        cod_limpo = cod_limpo[:-1]
        
    cursor.execute("SELECT texto FROM estrutura WHERE matricula = ? AND (codigo = ? OR codigo = ?)", (matricula, cod_limpo, f"{cod_limpo}."))
    resultado = cursor.fetchone()
    return resultado[0] if resultado else "Não localizado na árvore atual"

# --- GERADOR DE PDF PROFISSIONAL ---
class ProfessionalPDF(FPDF):
    def __init__(self, orgao, emitente, membros):
        super().__init__()
        self.orgao = orgao
        self.emitente = emitente
        self.membros = membros
        self.data_emissao = datetime.now().strftime("%d/%m/%Y %H:%M")

    def header(self):
        self.set_font('Arial', 'B', 10)
        self.cell(0, 5, 'UNIVERSIDADE FEDERAL FLUMINENSE', 0, 1, 'C')
        self.cell(0, 5, 'INSTITUTO DE ARTE E COMUNICAÇÃO SOCIAL', 0, 1, 'C')
        self.cell(0, 5, 'DEPARTAMENTO DE CIÊNCIA DA INFORMAÇÃO', 0, 1, 'C')
        self.cell(0, 5, 'CURSO DE GRADUAÇÃO EM ARQUIVOLOGIA', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'DISCIPLINA DE TÓPICOS ESPECIAIS 1', 0, 1, 'C')
        self.cell(0, 5, 'PROFESSORES: CLARISSA SCHMIDT E PAULO ALENCAR', 0, 1, 'C')
        self.ln(10)
        self.line(10, 42, 200, 42)

    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.line(10, 275, 200, 275)
        self.cell(0, 10, self.encode_txt(f'Emitido por: {self.emitente} | Data: {self.data_emissao}'), 0, 0, 'L')
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'R')

    def encode_txt(self, texto):
        if not texto:
            return ""
        texto_limpo = str(texto).replace('–', '-').replace('—', '-')
        return texto_limpo.encode('latin-1', 'ignore').decode('latin-1')

def gerar_relatorio_final(orgao, emitente, matricula, membros, dados):
    pdf = ProfessionalPDF(orgao, emitente, membros)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 15, pdf.encode_txt("PLANO DE CLASSIFICAÇÃO DE DOCUMENTOS"), 0, 1, 'C')
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, pdf.encode_txt(f"ÓRGÃO PRODUTOR: {orgao.upper()}"), 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 8, " COMPONENTES DO GRUPO", 0, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, pdf.encode_txt(f"Líder / Responsável: {emitente} ({matricula})"), 0, 1, 'L')
    for m_nome, m_mat in membros:
        pdf.cell(0, 6, pdf.encode_txt(f"Integrante: {m_nome} ({m_mat})"), 0, 1, 'L')
    pdf.ln(8)

    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, " ESTRUTURA ARQUIVÍSTICA DO PLANO", 0, 1, 'L', fill=True)
    pdf.ln(4)
    
    # Ordenação estrita baseada nas partes numéricas dos códigos para não quebrar a hierarquia
    dados_ordenados = sorted(dados, key=lambda x: [int(p) for p in re.findall(r'\d+', x[1])])
    
    for _, cod, tipo, txt in dados_ordenados:
        # Define o recuo (margem esquerda) e a largura útil da célula de acordo com o nível
        if tipo == "Função":
            recuo_esquerdo = 10
            largura_util = 190
            pdf.set_font('Arial', 'B', 10)
        elif tipo == "Subfunção":
            recuo_esquerdo = 20
            largura_util = 180
            pdf.set_font('Arial', '', 10)
        elif tipo == "Atividade":
            recuo_esquerdo = 30
            largura_util = 170
            pdf.set_font('Arial', '', 10)
        else: # Tipo documental
            recuo_esquerdo = 40
            largura_util = 160
            pdf.set_font('Arial', 'I', 10)
        
        texto_linha = f"{cod} - {txt}"
        
        if pdf.get_y() > 245:
            pdf.add_page()
            
        # Posiciona horizontalmente respeitando o recuo estruturado
        pdf.set_x(recuo_esquerdo)
        pdf.multi_cell(largura_util, 6, pdf.encode_txt(texto_linha))
        
    return bytes(pdf.output())

# --- INTERFACE PRINCIPAL ---
st.title("Plano de Classificação Online - UFF")
menu = st.sidebar.radio("Navegação", ["Área do Aluno", "Área do Professor (Admin)"])

# ==========================================
#              ÁREA DO ALUNO
# ==========================================
if menu == "Área do Aluno":
    st.header("📝 Acesso do Estudante")
    
    if 'aluno_logado' not in st.session_state:
        opcao_acesso = st.radio("Selecione o modo de entrada:", ["Já Estou Cadastrado", "Primeiro Acesso (Criar Novo Perfil)"], horizontal=True)
        st.write("---")
        matricula_input = st.text_input("Digite sua Matrícula:", key="input_mat").strip()
        nome_input = st.text_input("Digite seu Nome Completo:", key="input_nome").strip()
        
        orgao_input = ""
        if opcao_acesso == "Primeiro Acesso (Criar Novo Perfil)":
            orgao_input = st.text_input("Nome da Instituição / Órgão do seu plano:", key="input_orgao").strip()
        
        st.write("##")
        if st.button("🚀 Entrar / Confirmar Cadastro no Sistema"):
            if not matricula_input or not nome_input:
                st.error("Por favor, preencha a Matrícula e o Nome Completo.")
            else:
                cursor.execute("SELECT nome, orgao FROM alunos WHERE matricula = ?", (matricula_input,))
                aluno_existente = cursor.fetchone()
                
                if opcao_acesso == "Já Estou Cadastrado":
                    if aluno_existente:
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
                        st.session_state.update({'aluno_matricula': matricula_input, 'aluno_nome': nome_input, 'aluno_orgao': orgao_input, 'aluno_logado': True})
                        st.success("Perfil gerado com sucesso!")
                        st.rerun()
                        
    else:
        st.info(f"Estudante Responsável: **{st.session_state['aluno_nome']}** | Matrícula: **{st.session_state['aluno_matricula']}** | Órgão: **{st.session_state['aluno_orgao']}**")
        if st.sidebar.button("🚪 Sair / Mudar de Conta"):
            del st.session_state['aluno_logado']
            st.rerun()
            
        st.write("---")
        st.header("📁 Gerenciamento do seu Plano de Classificação")
        
        tab1, tab2, tab3, tab4 = st.tabs(["👥 Integrantes do Grupo", "➕ Inserir Novos Elementos", "🔍 Visualizar & Editar Estrutura", "📄 Exportar em PDF"])
        
        # TAB 1: GRUPO
        with tab1:
            st.subheader("Componentes do Grupo de Trabalho")
            st.caption("Adicione os outros integrantes do seu grupo abaixo para que saiam listados no relatório oficial.")
            
            with st.form("form_membros", clear_on_submit=True):
                col_m_nome = st.text_input("Nome do Integrante:")
                col_m_mat = st.text_input("Matrícula do Integrante:")
                if st.form_submit_button("➕ Vincular Membro ao Grupo"):
                    if col_m_nome and col_m_mat:
                        cursor.execute("INSERT INTO membros_grupo (matricula_lider, nome_membro, matricula_membro) VALUES (?, ?, ?)", 
                                       (st.session_state['aluno_matricula'], col_m_nome.strip(), col_m_mat.strip()))
                        conn.commit()
                        st.success(f"{col_m_nome} adicionado!")
                    else:
                        st.error("Preencha ambos os campos para adicionar.")
            
            st.write("### 👥 Integrantes Cadastrados neste Grupo:")
            cursor.execute("SELECT id, nome_membro, matricula_membro FROM membros_grupo WHERE matricula_lider = ?", (st.session_state['aluno_matricula'],))
            membros_atuais = cursor.fetchall()
            
            if membros_atuais:
                for mid, mnome, mmat in membros_atuais:
                    col_list, col_btn = st.columns([6, 1])
                    col_list.write(f"• **{mnome}** (Matrícula: {mmat})")
                    if col_btn.button("🗑️", key=f"del_m_{mid}"):
                        cursor.execute("DELETE FROM membros_grupo WHERE id = ?", (mid,))
                        conn.commit()
                        st.rerun()
            else:
                st.info("Apenas o líder está no grupo atualmente. Adicione os colegas acima se houver.")

        # TAB 2: INSERÇÃO
        with tab2:
            st.subheader("Cadastrar Item na Árvore Hierárquica")
            tipo_item = st.selectbox("Nível Hierárquico:", ["Função", "Subfunção", "Atividade", "Tipo documental"])
            codigo_item = st.text_input("Código Numérico:", help="Ex: 01, 01.01., 01.01.01.").strip()
            texto_item = st.text_area("Descrição/Texto (Máx 250 caracteres):", max_chars=250)
            
            if codigo_item and texto_item:
                valido, formato_correto = validar_codigo(codigo_item, tipo_item)
                if not valido:
                    st.error(f"Código inválido para '{tipo_item}'. {formato_correto}")
                else:
                    cod_limpo = codigo_item[:-1] if codigo_item.endswith('.') else codigo_item
                    partes = cod_limpo.split('.')
                    mat_atual = st.session_state['aluno_matricula']
                    
                    aviso_popup = ""
                    if tipo_item == "Subfunção" and len(partes) >= 2:
                        f_nome = buscar_nome_elemento(mat_atual, partes[0])
                        aviso_popup = f"O código **{codigo_item}** vincula este elemento à **Função {partes[0]}** ({f_nome})."
                    elif tipo_item == "Atividade" and len(partes) >= 3:
                        f_nome = buscar_nome_elemento(mat_atual, partes[0])
                        sf_cod = f"{partes[0]}.{partes[1]}"
                        sf_nome = buscar_nome_elemento(mat_atual, sf_cod)
                        aviso_popup = f"O código **{codigo_item}** vincula à **Função {partes[0]}** ({f_nome}) e à **Subfunção {sf_cod}** ({sf_nome})."
                    elif tipo_item == "Tipo documental" and len(partes) >= 4:
                        f_nome = buscar_nome_elemento(mat_atual, partes[0])
                        sf_cod = f"{partes[0]}.{partes[1]}"
                        sf_nome = buscar_nome_elemento(mat_atual, sf_cod)
                        at_cod = f"{partes[0]}.{partes[1]}.{partes[2]}"
                        at_nome = buscar_nome_elemento(mat_atual, at_cod)
                        aviso_popup = f"O código **{codigo_item}** vincula à **Atividade {at_cod}** ({at_nome}) dentro de {sf_nome}."

                    if tipo_item == "Função":
                        if st.button("💾 Salvar Função"):
                            cursor.execute("INSERT INTO estrutura (matricula, tipo, codigo, texto) VALUES (?, ?, ?, ?)", (mat_atual, tipo_item, codigo_item, texto_item.strip()))
                            conn.commit()
                            st.success("Função cadastrada com sucesso!")
                            st.rerun()
                    else:
                        with st.popover("Clique aqui para Validar & Salvar"):
                            st.markdown(aviso_popup)
                            if st.button("Confirmar e Gravar Elemento"):
                                cursor.execute("INSERT INTO estrutura (matricula, tipo, codigo, texto) VALUES (?, ?, ?, ?)", (mat_atual, tipo_item, codigo_item, texto_item.strip()))
                                conn.commit()
                                st.success("Elemento gravado!")
                                st.rerun()
            else:
                st.info("Preencha o código numérico e a descrição para liberar o salvamento.")

        # TAB 3: VISUALIZAÇÃO E EDIÇÃO
        with tab3:
            st.subheader(f"Estrutura Atual: {st.session_state['aluno_orgao']}")
            cursor.execute("SELECT id, codigo, tipo, texto FROM estrutura WHERE matricula = ?", (st.session_state['aluno_matricula'],))
            dados = cursor.fetchall()
            
            if dados:
                dados_ordenados = sorted(dados, key=lambda x: [int(p) for p in re.findall(r'\d+', x[1])])
                for item_id, cod, tipo, txt in dados_ordenados:
                    if tipo == "Função": st.markdown(f"**{cod} {txt}**")
                    elif tipo == "Subfunção": st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📄 {cod} {txt}")
                    elif tipo == "Atividade": st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔹 {cod} {txt}")
                    elif tipo == "Tipo documental": st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;🔸 *{cod} {txt}*")
                
                st.write("---")
                st.subheader("🛠️ Painel de Modificações Rápidas (Aluno)")
                for item_id, cod, tipo, txt in dados_ordenados:
                    col_info, col_edit, col_del = st.columns([6, 2, 1])
                    col_info.write(f"`{cod}` **[{tipo}]** — {txt}")
                    with col_edit:
                        with st.expander("✏️ Editar"):
                            novo_texto = st.text_input("Alterar texto:", value=txt, key=f"txt_al_{item_id}")
                            if st.button("Confirmar", key=f"btn_edit_al_{item_id}"):
                                if novo_texto.strip():
                                    cursor.execute("UPDATE estrutura SET texto = ? WHERE id = ?", (novo_texto.strip(), item_id))
                                    conn.commit()
                                    st.success("Atualizado!")
                                    st.rerun()
                    if col_del.button("🗑️", key=f"btn_del_al_{item_id}"):
                        cursor.execute("DELETE FROM estrutura WHERE id = ?", (item_id,))
                        conn.commit()
                        st.warning("Removido!")
                        st.rerun()
            else:
                st.warning("Nenhum item adicionado à sua árvore hierárquica ainda.")

        # TAB 4: EXPORTAÇÃO PDF
        with tab4:
            st.subheader("📥 Exportação Oficial em PDF")
            cursor.execute("SELECT id, codigo, tipo, texto FROM estrutura WHERE matricula = ?", (st.session_state['aluno_matricula'],))
            dados_reais = cursor.fetchall()
            cursor.execute("SELECT nome_membro, matricula_membro FROM membros_grupo WHERE matricula_lider = ?", (st.session_state['aluno_matricula'],))
            membros_lista = cursor.fetchall()
            
            if dados_reais:
                try:
                    pdf_data = gerar_relatorio_final(st.session_state['aluno_orgao'], st.session_state['aluno_nome'], st.session_state['aluno_matricula'], membros_lista, dados_reais)
                    st.download_button(label="📄 Baixar Relatório Completo em PDF (UFF)", data=pdf_data, file_name=f"Plano_Classificacao_{st.session_state['aluno_orgao']}.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"Erro ao compilar o arquivo de impressão: {e}")
            else:
                st.warning("Não há dados estruturados para exportação.")

# ==========================================
#         ÁREA DO PROFESSOR (ADMIN)
# ==========================================
elif menu == "Área do Professor (Admin)":
    st.header("🔒 Painel Administrativo do Professor")
    
    if 'admin_logado' not in st.session_state:
        usuario = st.text_input("Usuário Admin:")
        senha = st.text_input("Senha Admin:", type="password")
        if st.button("Acessar Painel"):
            if usuario == "Admin123" and senha == "123Admin":
                st.session_state['admin_logado'] = True
                st.success("Acesso autorizado!")
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
    else:
        if st.sidebar.button("🚪 Sair do Painel Admin"):
            del st.session_state['admin_logado']
            st.rerun()
            
        st.subheader("📚 Alunos e Estruturas Cadastradas")
        cursor.execute("SELECT matricula, nome, orgao FROM alunos")
        lista_alunos = cursor.fetchall()
        
        if lista_alunos:
            for al_mat, al_nome, al_org in lista_alunos:
                cursor.execute("SELECT nome_membro, matricula_membro FROM membros_grupo WHERE matricula_lider = ?", (al_mat,))
                membros_al = cursor.fetchall()
                texto_membros = ", ".join([f"{n} ({m})" for n, m in membros_al]) if membros_al else "Apenas o líder"
                
                with st.expander(f"👤 Grupo de {al_nome} — Órgão: {al_org} (Membros: {texto_membros})"):
                    st.markdown("#### ⚠️ Controle do Perfil Completo")
                    if st.checkbox("Habilitar exclusão permanente deste estudante e grupo", key=f"chk_total_{al_mat}"):
                        if st.button(f"🔥 Apagar Conta e Dados de {al_nome}", key=f"btn_total_{al_mat}"):
                            cursor.execute("DELETE FROM estrutura WHERE matricula = ?", (al_mat,))
                            cursor.execute("DELETE FROM membros_grupo WHERE matricula_lider = ?", (al_mat,))
                            cursor.execute("DELETE FROM alunos WHERE matricula = ?", (al_mat,))
                            conn.commit()
                            st.success("Estudante e grupo excluídos!")
                            st.rerun()
                            
                    st.write("---")
                    st.markdown("#### 📁 Visualização e Modificação de Itens do Plano")
                    cursor.execute("SELECT id, codigo, tipo, texto FROM estrutura WHERE matricula = ?", (al_mat,))
                    itens_aluno = cursor.fetchall()
                    
                    if itens_aluno:
                        itens_ordenados = sorted(itens_aluno, key=lambda x: [int(p) for p in re.findall(r'\d+', x[1])])
                        for item_id, cod, tipo, txt in itens_ordenados:
                            col_dados, col_prof_edit, col_prof_del = st.columns([5, 3, 1])
                            col_dados.write(f"**{cod}** `[{tipo}]` — {txt}")
                            with col_prof_edit:
                                with st.popover("✏️ Corrigir Texto"):
                                    txt_professor = st.text_input("Alterar descrição:", value=txt, key=f"prof_in_{item_id}")
                                    if st.button("Salvar Correção", key=f"prof_btn_sav_{item_id}"):
                                        if txt_professor.strip():
                                            cursor.execute("UPDATE estrutura SET texto = ? WHERE id = ?", (txt_professor.strip(), item_id))
                                            conn.commit()
                                            st.success("Texto corrigido!")
                                            st.rerun()
                            if col_prof_del.button("🗑️", key=f"prof_del_it_{item_id}"):
                                cursor.execute("DELETE FROM estrutura WHERE id = ?", (item_id,))
                                conn.commit()
                                st.warning("Item deletado!")
                                st.rerun()
                    else:
                        st.info("Este grupo ainda não cadastrou nenhum elemento na estrutura.")
        else:
            st.info("Nenhum estudante realizou cadastro no sistema até o momento.")

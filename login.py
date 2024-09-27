import streamlit as st
from PIL import Image

def autenticar(usuario, senha):
    usuarios_validos = {
        "charles": "123",
        "Noam": "123",
        "Lael": "123"
    }
    if usuario not in usuarios_validos:
        return False, "Usuário inválido"
    elif usuarios_validos[usuario] != senha:
        return False, "Senha inválida"
    else:
        return True, ""

def render():

    with open("login.css") as f:    
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)  

    logo = Image.open('logo.png')
    st.image(logo, width=230)
    
    faca_login = '''
    <div class="d-grid gap-2" >        
        <p class="fs-2 text-center" class="mt-3">Faça Login</p>
    </div>
    '''
    st.markdown(faca_login, unsafe_allow_html=True)


    usuario = st.text_input("Usuário", key="usuario_input")
    senha = st.text_input("Senha", type="password", key="senha_input")
    


    if st.button("Entrar"):
        sucesso, mensagem = autenticar(usuario, senha)
        if sucesso:
            st.session_state["autenticado"] = True
            st.session_state["pagina"] = "Testes"
            st.experimental_rerun()
        else:
            st.session_state["autenticado"] = False
            st.error(mensagem)

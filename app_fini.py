import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pyodbc
import locale
from PIL import Image
import altair as alt
import numpy as np 
import time
import random
import hmac

# Configure a localidade
locale.setlocale(locale.LC_ALL, 'pt_BR')

# Configurações da página
st.set_page_config(
    page_title="DASHBOARD RJ DISTRIBUIDORA",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# conexão com o banco de dados
@st.cache_data
def banco(database_name, ano, secao):
    server = st.secrets["db_server"]  
    username = st.secrets["db_username"]
    password = st.secrets["db_password"]

    # String de conexão    
    conn_str = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database_name};UID={username};PWD={password}'

    # Estabelece a conexão
    connection = pyodbc.connect(conn_str)

    query = f"""
    SELECT Ano, Mês, Seção,
        COALESCE(SUM(Faturamento), 0) AS 'Faturamento',  
        COALESCE(SUM(Positivação), 0) AS 'Positivação'
    FROM (
        SELECT 
            cal.cal_ano AS 'Ano', 
            cal.cal_mes AS 'Mês', 
            d.pc_secao_descr_ AS 'Seção',
            SUM(b.vi_qtd * b.vi_valorunit) AS 'Faturamento',	
            COUNT(DISTINCT(a.cl_codigo)) AS 'Positivação',
            vd_data_venda As 'data'    
        FROM         
            t_calendar cal
        INNER JOIN
            t_vendas a ON a.vd_data_venda = cal.cal_data
        INNER JOIN 
            t_vendas_itens b ON a.vd_codigo = b.vd_codigo
        INNER JOIN
            t_produtos c ON c.pr_codigo = b.pr_codigo
        INNER JOIN 
            t_produtos_class d ON c.pc_codigo = d.pc_codigo
        INNER JOIN 
            t_clientes e ON a.cl_codigo = e.cl_codigo
        INNER JOIN
            t_estrutura f ON a.es_id = f.es_id
        WHERE
            cal.cal_ano = {ano}
            AND a.vd_status <> 12
            AND a.vd_bonif = 0
            AND d.pc_secao_descr_ = '{secao}'
            AND a.vd_data_venda = cal.cal_data
            AND (
                ('{database_name}' = 'WiBiERP_CAR' AND f.es_regiao IN (1, 2, 3)) OR
                ('{database_name}' = 'WiBiERP_FOR' AND f.es_regiao IN (1, 2, 4, 5)) OR
                ('{database_name}' = 'WiBiERP_QUI' AND f.es_regiao IN (1, 2)) OR
                ('{database_name}' = 'WiBiERP_SOB' AND f.es_regiao IN (1, 2, 3)) OR
                ('{database_name}' = 'WiBiERP_SLS' AND f.es_regiao IN (1, 2, 3, 4, 6, 8, 9))
            )
            AND e.tp_status = 1 -- Certifica-se de contar apenas os clientes ativos	
        GROUP BY 
            cal.cal_ano, cal.cal_mes, d.pc_secao_descr_, vd_data_venda
    ) AS Subconsulta
    GROUP BY 
        Ano, Mês, Seção
    ORDER BY
        Ano, Mês;
"""

    # Carrega os dados em um DataFrame
    df = pd.read_sql_query(query, connection)

    # Fecha a conexão
    connection.close()

    df['Mês'] = df['Mês'].apply(lambda x: pd.Timestamp(f'2024-{x:02d}-01').strftime('%B'))

    month_order = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    df['Mês'] = pd.Categorical(df['Mês'], categories=month_order, ordered=True)

    # Formata os números para o formato brasileiro
    df['Faturamento Formatado'] = df['Faturamento'].apply(lambda x: locale.format_string('%.2f', x, grouping=True))
    
    # Adiciona uma coluna com o nome do banco de dados
    df['Banco de Dados'] = database_name

    return df.reset_index()

# Sidebar
with st.sidebar:
    logo_image = Image.open('logo.png')
    st.image(logo_image, width=230)
    st.markdown("___")
    ano_input = st.text_input('Digite o Ano:')
    option = st.selectbox(
    "Selecione: ",
    ['FINI', 'BELLAVANA', 'RICLAN',]
    )   

if ano_input and option:

    my_bar = st.progress(0)
    percent_text = st.empty()

    for percent_complete in range(100):
        time.sleep(0.1)
        my_bar.progress(percent_complete + 1)
        percent_text.text(f"{percent_complete + 1}% concluído")
    
    # Lista de bancos de dados
    databases = ['WiBiERP_CAR','WiBiERP_FOR', 'WiBiERP_QUI','WiBiERP_SOB','WiBiERP_SLS']

    cariri = banco('WiBiERP_CAR', ano_input, secao=option)
    fortaleza = banco('WiBiERP_FOR', ano_input, secao=option)
    quixada = banco('WiBiERP_QUI', ano_input, secao=option)
    sobral = banco('WiBiERP_SOB', ano_input, secao=option)
    sao_luis = banco('WiBiERP_SLS', ano_input, secao=option)     
  
    ## ------------------------------------------------ PAGINA PRINCIPAL ------------------------------------------------------------------------------
    st.markdown(":bar_chart")
    st.markdown(
    # ---------------------------------------------- Titulo da pagina dashboadr -----------------------------------------------------------------------
    "<h1 style='text-align: center; font-size: 32px; color: #1a5fb8;'>DASHBOARD DE VENDAS RJ DISTRIBUIDORA</h1>", 
    unsafe_allow_html=True)
    st.markdown("___")
    # --------------------------------------------------------- FIM do titulo -------------------------------------------------------------------------

    # ----------------------------------------------------- Dados para o gráfico de pizza Cariri ------------------------------------------------------#
    st.markdown(
    "<h2 style='text-align: center; font-size: 24px; color: #1a5fb8;'>RJ CARIRI</h2>", 
    unsafe_allow_html=True
    )
    
    labels = cariri['Mês']
    values = cariri['Faturamento']

    # Definindo ordens
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    # Reordenando a ordem dos meses
    cariri['Mês'] = pd.Categorical(cariri['Mês'], categories=meses, ordered=True)
    cariri = cariri.sort_values('Mês')

    # Atualizando os dados
    labels = cariri['Mês']
    values = cariri['Faturamento']

    # Função para formatar os valores em reais
    def format_real(valor):
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

    # Aplicando a função de formatação para os valores
    formatted_values = [format_real(v) for v in values]

    # Definindo manualmente as cores para cada fatia do gráfico
    colors = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA", 
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880", 
        "#FF97FF", "#FECB52", "#AADEA7", "#EB89B5"
    ]

    # Personalização do gráfico
    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        hole=0.3, 
        pull=[0.1] * len(labels),
        textinfo='label+percent',  # Inclui os nomes dos meses e os percentuais dentro do gráfico
        marker=dict(colors=colors)  # Aplicando as cores manualmente
    )])

    # Configurando layout do gráfico
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=30),
        showlegend=False  # Desativa a legenda automática do gráfico
    )

    fig.update_layout(annotations=[dict(
    text='Faturamento Mês',
    x=0.5,
    y=0.5,
    font=dict(size=18, color='blue', family='Arial', weight='bold'),
    showarrow=False
    )])

    # Exibindo o gráfico e a legenda personalizada abaixo dele
    st.plotly_chart(fig)

    # Exibindo a legenda personalizada abaixo do gráfico em uma linha horizontal
    
    legend_html = "<div style='display: flex; justify-content: center; flex-wrap: wrap;'>"
    for i, (mes, valor) in enumerate(zip(labels, formatted_values)):
        color = colors[i]
        legend_html += f"<div style='margin: 5px; text-align: center;'><span style='color:{color}'>{mes.capitalize()}</span><br>{valor}</div>"
    legend_html += "</div>"
    st.write(legend_html, unsafe_allow_html=True)

    st.markdown("___")

    # ---------------------------------------------------- FIM DO GRAFICO DE PIZZA --------------------------------------------------

    # ----------------------------------------------------- GRAFICO DE LINHAS CARIRI ------------------------------------------------
    #grafico de linhas CARIRI
    graf_cariri_linha = alt.Chart(cariri).mark_line(
        color='#000fff',
    ).encode(
        x='Mês',
        y='Faturamento',
    ).properties(height=460)
    ln1=graf_cariri_linha.mark_text(radius=12, size=14).encode(text='Faturamento Formatado')
    # ----------------------------------------------------- FIM DO GRAFICO DE LINHAS CARIRI ------------------------------------------------

    # ----------------------------------------------------- GRAFICO DE POSITIVAÇÃO  CARIRI ------------------------------------------------
    
    graf_pos_car = alt.Chart(cariri).mark_bar(
        color='#adcfff',
        cornerRadiusTopLeft=9,
        cornerRadiusTopRight=9,        
    ).encode(
        x='Mês',
        y='Positivação'
    ).properties(height=460)

    # Adiciona texto no gráfico
    text_car = graf_pos_car.mark_text(
        radius=12,
        size=14
    ).encode(
        text='Positivação'
    )

    # Combina o gráfico de barras com o texto
    graf_pos_car_final = alt.layer(
        graf_pos_car, 
        text_car
    ).configure_axis(
        grid=False  # Remove as linhas de grade de ambos os eixos
    )  
    # ----------------------------------------------------- FIM DO GRAFICO POSITIVAÇÃO  CARIRI ------------------------------------------------

    # ------------------------------------------------------ COLUNAS CARIRI ----------------------------------------------------------------
    col1, col2,  = st.columns([1, 1,])
  
    with col1:
        st.markdown(
        "<h3 style='text-align: center; font-size: 24px; color: #1a5fb8;'>Estatística Cariri</h3>", 
        unsafe_allow_html=True)
        st.altair_chart(graf_cariri_linha+ln1, use_container_width=True)
    
    with col2:
        st.markdown(
        "<h3 style='text-align: center; font-size: 24px; color: #1a5fb8;'>Positivação Cariri</h3>", 
        unsafe_allow_html=True)
        st.altair_chart(graf_pos_car_final+text_car, use_container_width=True) 

    st.markdown("___")
    # ------------------------------------------------------ FIM COLUNAS CARIRI ----------------------------------------------------------------
    
    # ------------------------------------------------------ GRAFICOS FORTALEZA -----------------------------------------------------------------
    
    # -----------------------------------------------------  Gráfico de pizza Fortaleza ----------------------------------------------------#
    st.markdown(
    "<h2 style='text-align: center; font-size: 24px; color: #1a5fb8;'>RJ FORTALEZA</h2>", 
    unsafe_allow_html=True
    )
    
    labels = fortaleza['Mês']
    values = fortaleza['Faturamento']

    # Definindo ordens
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    # Reordenando a ordem dos meses
    fortaleza['Mês'] = pd.Categorical(fortaleza['Mês'], categories=meses, ordered=True)
    fortaleza = fortaleza.sort_values('Mês')

    # Atualizando os dados
    labels = fortaleza['Mês']
    values = fortaleza['Faturamento']

    # Função para formatar os valores em reais
    def format_real(valor):
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

    # Aplicando a função de formatação para os valores
    formatted_values = [format_real(v) for v in values]

    # Definindo manualmente as cores para cada fatia do gráfico
    colors = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA", 
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880", 
        "#FF97FF", "#FECB52", "#AADEA7", "#EB89B5"
    ]

    # Personalização do gráfico
    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        hole=0.3, 
        pull=[0.1] * len(labels),
        textinfo='label+percent',  # Inclui os nomes dos meses e os percentuais dentro do gráfico
        marker=dict(colors=colors)  # Aplicando as cores manualmente
    )])

    # Configurando layout do gráfico
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=30),
        showlegend=False  # Desativa a legenda automática do gráfico
    )

    fig.update_layout(annotations=[dict(
    text='Faturamento Mês',
    x=0.5,
    y=0.5,
    font=dict(size=18, color='blue', family='Arial', weight='bold'),
    showarrow=False
    )])


    # Exibindo o gráfico e a legenda personalizada abaixo dele
    st.plotly_chart(fig)

    # Exibindo a legenda personalizada abaixo do gráfico em uma linha horizontal
    
    legend_html = "<div style='display: flex; justify-content: center; flex-wrap: wrap;'>"
    for i, (mes, valor) in enumerate(zip(labels, formatted_values)):
        color = colors[i]
        legend_html += f"<div style='margin: 5px; text-align: center;'><span style='color:{color}'>{mes.capitalize()}</span><br>{valor}</div>"
    legend_html += "</div>"
    st.write(legend_html, unsafe_allow_html=True)

    st.markdown("___")

    # ---------------------------------------------------- FIM DO GRAFICO DE PIZZA --------------------------------------------------

    #grafico de linhas FORTALEZA
    graf_fortaleza_linha = alt.Chart(fortaleza).mark_line(
        color='#000fff',
    ).encode(
        x='Mês',
        y='Faturamento',
    ).properties(height=460)
    ln1_for=graf_fortaleza_linha.mark_text(radius=20,size=14).encode(text='Faturamento Formatado')    
    # FIM grafico de linhas Fortaleza

    # ------------------------------------------------------Gráfico de POSITIVAÇÃO Fortaleza ------------------------------------------------------
    graf_pos_for = alt.Chart(fortaleza).mark_bar(
        color='#adcfff',
        cornerRadiusTopLeft=9,
        cornerRadiusTopRight=9,        
    ).encode(
        x='Mês',
        y='Positivação'
    ).properties(height=460)
   

    # Adiciona texto no gráfico
    text_for = graf_pos_for.mark_text(
        radius=20,
        size=14
    ).encode(
        text='Positivação'
    )

    # Combina o gráfico de barras com o texto
    graf_pos_for_final = alt.layer(
        graf_pos_for, 
        text_for
    ).configure_axis(
        grid=False  # Remove as linhas de grade de ambos os eixos
    )
     # -------------------------------------------------------FIM Gráfico Fortaleza Positivação ---------------------------------------------------------------------

    # ------------------------------------------------------ FIM DOS GRAFICOS FORTALEZA -----------------------------------------------------------------
    
    col1, col2,  = st.columns([1, 1,])            

    with col1:
        st.markdown(
        "<h3 style='text-align: center; font-size: 24px; color: #1a5fb8;'>Estatística Fortaleza</h3>", 
        unsafe_allow_html=True)
        st.altair_chart(graf_fortaleza_linha+ln1, use_container_width=True)

    with col2:
        st.markdown(
        "<h3 style='text-align: center; font-size: 24px; color: #1a5fb8;'>Positivação Fortaleza</h3>", 
        unsafe_allow_html=True)
        st.altair_chart(graf_pos_for_final+text_for, use_container_width=True)

    st.markdown("___")

    # ------------------------------------------------------ FIM LINHAS FORTALEZA -----------------------------------------------------------------
    
    # -------------------------------------------------------GRAFCICOS QUIXADA --------------------------------------------------------------

     # -----------------------------------------------------  Gráfico de pizza Quixada ----------------------------------------------------#
    st.markdown(
    "<h2 style='text-align: center; font-size: 24px; color: #1a5fb8;'>RJ QUIXADÁ</h2>", 
    unsafe_allow_html=True
    )
    
    labels = quixada['Mês']
    values = quixada['Faturamento']

    # Definindo ordens
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    # Reordenando a ordem dos meses
    quixada['Mês'] = pd.Categorical(quixada['Mês'], categories=meses, ordered=True)
    quixada = quixada.sort_values('Mês')

    # Atualizando os dados
    labels = quixada['Mês']
    values = quixada['Faturamento']

    # Função para formatar os valores em reais
    def format_real(valor):
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

    # Aplicando a função de formatação para os valores
    formatted_values = [format_real(v) for v in values]

    # Definindo manualmente as cores para cada fatia do gráfico
    colors = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA", 
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880", 
        "#FF97FF", "#FECB52", "#AADEA7", "#EB89B5"
    ]

    # Personalização do gráfico
    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        hole=0.3, 
        pull=[0.1] * len(labels),
        textinfo='label+percent',  # Inclui os nomes dos meses e os percentuais dentro do gráfico
        marker=dict(colors=colors)  # Aplicando as cores manualmente
    )])

    # Configurando layout do gráfico
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=30),
        showlegend=False  # Desativa a legenda automática do gráfico
    )

    fig.update_layout(annotations=[dict(
    text='Faturamento Mês',
    x=0.5,
    y=0.5,
    font=dict(size=18, color='blue', family='Arial', weight='bold'),
    showarrow=False
    )])

    # Exibindo o gráfico e a legenda personalizada abaixo dele
    st.plotly_chart(fig)

    # Exibindo a legenda personalizada abaixo do gráfico em uma linha horizontal
    
    legend_html = "<div style='display: flex; justify-content: center; flex-wrap: wrap;'>"
    for i, (mes, valor) in enumerate(zip(labels, formatted_values)):
        color = colors[i]
        legend_html += f"<div style='margin: 5px; text-align: center;'><span style='color:{color}'>{mes.capitalize()}</span><br>{valor}</div>"
    legend_html += "</div>"
    st.write(legend_html, unsafe_allow_html=True)

    st.markdown("___")

    # ---------------------------------------------------- FIM DO GRAFICO DE PIZZA QUIXADA --------------------------------------------------

    #------------------------------------------------------ grafico de linhas QUIXADA
    graf_quixada_linha = alt.Chart(quixada).mark_line(
        color='#000fff',
    ).encode(
        x='Mês',
        y='Faturamento',
    ).properties(height=460)
    ln1=graf_quixada_linha.mark_text(radius=20,size=16).encode(text='Faturamento Formatado')
    # ------------------------------------------------------ FIM grafico de linhas QUIXADA

    # ------------------------------------------------------Gráfico de POSITIVAÇÃO QUIXADA ------------------------------------------------------
    graf_pos_qui = alt.Chart(quixada).mark_bar(
        color='#adcfff',
        cornerRadiusTopLeft=9,
        cornerRadiusTopRight=9,        
    ).encode(
        x='Mês',
        y='Positivação'
    ).properties(height=460)
   

    # Adiciona texto no gráfico
    text_qui = graf_pos_qui.mark_text(
        radius=20,
        size=14
    ).encode(
        text='Positivação'
    )

    # Combina o gráfico de barras com o texto
    graf_pos_qui_final = alt.layer(
        graf_pos_qui, 
        text_qui
    ).configure_axis(
        grid=False  # Remove as linhas de grade de ambos os eixos
    )
    # -------------------------------------------------------FIM Gráfico POSTIVAÇAO QUIXADA ------------------------------------------------
    # -------------------------------------------------------FIM GRAFCICOS QUIXADA ----------------------------------------------------------

    # ------------------------------------------------------ COLUNAS QUIXADA -----------------------------------------------------------------
      
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(
        "<h3 style='text-align: center; font-size: 24px; color: #1a5fb8;'>Estatística Quixadá</h3>", 
        unsafe_allow_html=True)
        st.altair_chart(graf_quixada_linha+ln1, use_container_width=True)
    
    with col2:
        st.markdown(
        "<h3 style='text-align: center; font-size: 24px; color: #1a5fb8;'>Positivação Quixadá</h3>", 
        unsafe_allow_html=True)
        st.altair_chart(graf_pos_qui_final+text_qui, use_container_width=True)
    st.markdown("___")
    
    # ------------------------------------------------------ FIM COLUNAS QUIXADA -----------------------------------------------------------------
    
    # ------------------------------------------------------ GRAFICOS SOBRAL -----------------------------------------------------------------
    
    # -----------------------------------------------------  Gráfico de pizza Sobral ----------------------------------------------------#
    st.markdown(
    "<h2 style='text-align: center; font-size: 24px; color: #1a5fb8;'>RJ SOBRAL</h2>", 
    unsafe_allow_html=True
    )
    
    labels = sobral['Mês']
    values = sobral['Faturamento']

    # Definindo ordens
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    # Reordenando a ordem dos meses
    sobral['Mês'] = pd.Categorical(sobral['Mês'], categories=meses, ordered=True)
    sobral = sobral.sort_values('Mês')

    # Atualizando os dados
    labels = sobral['Mês']
    values = sobral['Faturamento']

    # Função para formatar os valores em reais
    def format_real(valor):
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

    # Aplicando a função de formatação para os valores
    formatted_values = [format_real(v) for v in values]

    # Definindo manualmente as cores para cada fatia do gráfico
    colors = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA", 
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880", 
        "#FF97FF", "#FECB52", "#AADEA7", "#EB89B5"
    ]

    # Personalização do gráfico
    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        hole=0.3, 
        pull=[0.1] * len(labels),
        textinfo='label+percent',  # Inclui os nomes dos meses e os percentuais dentro do gráfico
        marker=dict(colors=colors)  # Aplicando as cores manualmente
    )])

    # Configurando layout do gráfico
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=30),
        showlegend=False  # Desativa a legenda automática do gráfico
    )

    fig.update_layout(annotations=[dict(
    text='Faturamento Mês',
    x=0.5,
    y=0.5,
    font=dict(size=18, color='blue', family='Arial', weight='bold'),
    showarrow=False
    )])


    # Exibindo o gráfico e a legenda personalizada abaixo dele
    st.plotly_chart(fig)

    # Exibindo a legenda personalizada abaixo do gráfico em uma linha horizontal
    
    legend_html = "<div style='display: flex; justify-content: center; flex-wrap: wrap;'>"
    for i, (mes, valor) in enumerate(zip(labels, formatted_values)):
        color = colors[i]
        legend_html += f"<div style='margin: 5px; text-align: center;'><span style='color:{color}'>{mes.capitalize()}</span><br>{valor}</div>"
    legend_html += "</div>"
    st.write(legend_html, unsafe_allow_html=True)

    st.markdown("___")

    # ---------------------------------------------------- FIM DO GRAFICO DE PIZZA SOBRAL --------------------------------------------------

    # ------------------------------------------------------Gráfico de POSITIVAÇÃO SOBRAL ------------------------------------------------------
    graf_pos_sob = alt.Chart(sobral).mark_bar(
        color='#adcfff',
        cornerRadiusTopLeft=9,
        cornerRadiusTopRight=9,        
    ).encode(
        x='Mês',
        y='Positivação'
    ).properties(height=460)
   

    # Adiciona texto no gráfico
    text_sob = graf_pos_sob.mark_text(
        radius=20,
        size=14
    ).encode(
        text='Positivação'
    )

    # Combina o gráfico de barras com o texto
    graf_pos_sob_final = alt.layer(
        graf_pos_sob, 
        text_sob
    ).configure_axis(
        grid=False  # Remove as linhas de grade de ambos os eixos
    )
     # -------------------------------------------------------FIM Gráfico POSTIVAÇAO SOBRAL ------------------------------------------------

    #grafico de linhas SOBRAL
    graf_sobral_linha = alt.Chart(sobral).mark_line(
        color='#000fff',
    ).encode(
        x='Mês',
        y='Faturamento',
    ).properties(height=460)
    ln1=graf_sobral_linha.mark_text(radius=20,size=16).encode(text='Faturamento Formatado')
    # FIM grafico de linhas SOBRAL    
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(
        "<h3 style='text-align: center; font-size: 24px; color: #1a5fb8;'>Estatística Sobral</h3>", 
        unsafe_allow_html=True)
        st.altair_chart(graf_sobral_linha+ln1, use_container_width=True)       

    with col2:
        st.markdown(
        "<h3 style='text-align: center; font-size: 24px; color: #1a5fb8;'>Positivação Sobral</h3>", 
        unsafe_allow_html=True)
        st.altair_chart(graf_pos_sob_final+text_sob, use_container_width=True)

    # ------------------------------------------------------ FIM COLUNAS FORTALEZA -----------------------------------------------------------------
    
    # ------------------------------------------------------ COLUNAS SÃO LUIS -----------------------------------------------------------------
    

    # -----------------------------------------------------  Gráfico de pizza São Luis ----------------------------------------------------#
    st.markdown(
    "<h2 style='text-align: center; font-size: 24px; color: #1a5fb8;'>RJ SÃO LUIS</h2>", 
    unsafe_allow_html=True
    )
    
    labels = sao_luis['Mês']
    values = sao_luis['Faturamento']

    # Definindo ordens
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    # Reordenando a ordem dos meses
    sao_luis['Mês'] = pd.Categorical(sao_luis['Mês'], categories=meses, ordered=True)
    sao_luis = sao_luis.sort_values('Mês')

    # Atualizando os dados
    labels = sao_luis['Mês']
    values = sao_luis['Faturamento']

    # Função para formatar os valores em reais
    def format_real(valor):
        return f"R$ {valor:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")

    # Aplicando a função de formatação para os valores
    formatted_values = [format_real(v) for v in values]

    # Definindo manualmente as cores para cada fatia do gráfico
    colors = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA", 
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880", 
        "#FF97FF", "#FECB52", "#AADEA7", "#EB89B5"
    ]

    # Personalização do gráfico
    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        hole=0.3, 
        pull=[0.1] * len(labels),
        textinfo='label+percent',  # Inclui os nomes dos meses e os percentuais dentro do gráfico
        marker=dict(colors=colors)  # Aplicando as cores manualmente
    )])

    # Configurando layout do gráfico
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=30),
        showlegend=False  # Desativa a legenda automática do gráfico
    )

    fig.update_layout(annotations=[dict(
    text='Faturamento Mês',
    x=0.5,
    y=0.5,
    font=dict(size=18, color='blue', family='Arial', weight='bold'),
    showarrow=False
    )])


    # Exibindo o gráfico e a legenda personalizada abaixo dele
    st.plotly_chart(fig)

    # Exibindo a legenda personalizada abaixo do gráfico em uma linha horizontal
    
    legend_html = "<div style='display: flex; justify-content: center; flex-wrap: wrap;'>"
    for i, (mes, valor) in enumerate(zip(labels, formatted_values)):
        color = colors[i]
        legend_html += f"<div style='margin: 5px; text-align: center;'><span style='color:{color}'>{mes.capitalize()}</span><br>{valor}</div>"
    legend_html += "</div>"
    st.write(legend_html, unsafe_allow_html=True)

    st.markdown("___")

    # ---------------------------------------------------- FIM DO GRAFICO DE PIZZA SÃO LUIS --------------------------------------------------

    # ------------------------------------------------------Gráfico de POSITIVAÇÃO SÃO LUIS ------------------------------------------------------
    graf_pos_sls = alt.Chart(sao_luis).mark_bar(
        color='#adcfff',
        cornerRadiusTopLeft=9,
        cornerRadiusTopRight=9,        
    ).encode(
        x='Mês',
        y='Positivação'
    ).properties(height=460)
   

    # Adiciona texto no gráfico
    text_sls = graf_pos_sls.mark_text(
        radius=20,
        size=14
    ).encode(
        text='Positivação'
    )

    # Combina o gráfico de barras com o texto
    graf_pos_sls_final = alt.layer(
        graf_pos_sls, 
        text_sls
    ).configure_axis(
        grid=False  # Remove as linhas de grade de ambos os eixos
    )
     # -------------------------------------------------------FIM Gráfico POSTIVAÇAO SÃO LUISL ------------------------------------------------

    #grafico de linhas SÃO LUIS
    graf_sao_luis_linha = alt.Chart(sao_luis).mark_line(
        color='#000fff',
    ).encode(
        x='Mês',
        y='Faturamento',
    ).properties(height=460)
    ln1=graf_sao_luis_linha.mark_text(radius=20,size=16).encode(text='Faturamento Formatado')
    # FIM grafico de linhas SÃO LUIS

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown(
        "<h3 style='text-align: center; font-size: 24px; color: #1a5fb8;'>Estatística São Luis</h3>", 
        unsafe_allow_html=True)
        st.altair_chart(graf_sao_luis_linha+ln1, use_container_width=True)            

    with col2:
        st.markdown(
        "<h3 style='text-align: center; font-size: 24px; color: #1a5fb8;'>Positivação São Luis</h3>", 
        unsafe_allow_html=True)
        st.altair_chart(graf_pos_sls_final+text_sls, use_container_width=True)    
    # ------------------------------------------------------ FIM COLUNAS SÃO LUIS -----------------------------------------------------------------
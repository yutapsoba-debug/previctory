import streamlit as st
import requests
import numpy as np
import pandas as pd
from scipy.stats import poisson

# Configurazione della pagina in modalità WIDE per un look professionale
st.set_page_config(page_title="PreVictory Pro", page_icon="⚽", layout="wide")

# Stile CSS personalizzato
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .main-title { font-size: 38px; font-weight: bold; color: #1E3A8A; text-align: center; margin-bottom: 5px; }
    .subtitle { font-size: 18px; color: #4B5563; text-align: center; margin-bottom: 25px; }
    .section-header { font-size: 22px; font-weight: bold; color: #1E3A8A; margin-top: 15px; margin-bottom: 10px; border-bottom: 2px solid #3B82F6; padding-bottom: 5px; }
    .card-info { background-color: #EFF6FF; padding: 15px; border-radius: 10px; border-left: 5px solid #3B82F6; margin-bottom: 15px; }
    .card-success { background-color: #ECFDF5; padding: 15px; border-radius: 10px; border-left: 5px solid #10B981; margin-bottom: 15px; }
    .card-warning { background-color: #FFFBEB; padding: 15px; border-radius: 10px; border-left: 5px solid #F59E0B; margin-bottom: 15px; }
    .card-danger { background-color: #FEF2F2; padding: 15px; border-radius: 10px; border-left: 5px solid #EF4444; margin-bottom: 15px; }
    .stProgress > div > div > div > div { background-color: #3B82F6; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">⚽ PreVictory</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Modello Poisson Avanzato + Logistica Logistica e Info Match</div>', unsafe_allow_html=True)

API_KEY = "c5a0956345da46beba916e7c9b23f2db"
headers = { 'X-Auth-Token': API_KEY }
CAMPIONATO = 'WC'

# STADI ED EMITTENTI ASSOCIATE PER IL TORNEO 2026
mappa_stadi = {
    'Mexico': 'Estadio Azteca (Città del Messico, MEX)',
    'Portugal': 'AT&T Stadium (Arlington, Dallas, USA)',
    'Spain': 'AT&T Stadium (Arlington, Dallas, USA)',
    'England': 'Estadio Azteca (Città del Messico, MEX)',
    'USA': 'Lumen Field (Seattle, USA)',
    'Belgium': 'Lumen Field (Seattle, USA)',
    'Argentina': 'Mercedes-Benz Stadium (Atlanta, USA)',
    'Netherlands': 'NRG Stadium (Houston, USA)',
    'France': 'MetLife Stadium (East Rutherford, NJ, USA)',
    'Brazil': 'MetLife Stadium (East Rutherford, NJ, USA)',
}

def ottieni_stadio(casa, ospite):
    if casa in mappa_stadi: return mappa_stadi[casa]
    if ospite in mappa_stadi: return mappa_stadi[ospite]
    return "Stadio Principale (USA / Canada / Messico)"

# DATABASE STATISTICO TIRI REALI (FBref)
dati_tiri_fbref = {
    'Brazil': (16.4, 6.2), 'Argentina': (14.8, 5.8), 'France': (15.1, 5.5),
    'England': (14.5, 5.2), 'Spain': (14.2, 5.1), 'Portugal': (14.1, 5.3),
    'Netherlands': (11.5, 4.0), 'Croatia': (10.8, 3.7), 'Morocco': (9.2, 3.1),
    'Italy': (12.6, 4.2), 'Germany': (16.1, 5.9), 'Belgium': (11.8, 4.1),
    'Uruguay': (11.2, 3.8), 'Japan': (10.5, 3.9), 'Senegal': (10.9, 3.6),
    'Switzerland': (11.0, 3.8)
}
MEDIA_TIRI_TORNEO = 12.5
MEDIA_PORTA_TORNEO = 4.2

fasce_squadre = {
    'Brazil': 1, 'Argentina': 1, 'France': 1, 'England': 1, 'Spain': 1, 'Portugal': 1, 'Germany': 1, 'Italy': 1,
    'Netherlands': 2, 'Croatia': 2, 'Belgium': 2, 'Uruguay': 2, 'Switzerland': 2,
    'Morocco': 3, 'Japan': 3, 'Senegal': 3
}

@st.cache_data(ttl=3600)
def carica_dati():
    try:
        url_matches = f"https://api.football-data.org/v4/competitions/{CAMPIONATO}/matches"
        data_matches = requests.get(url_matches, headers=headers).json()
        url_scorers = f"https://api.football-data.org/v4/competitions/{CAMPIONATO}/scorers"
        data_scorers = requests.get(url_scorers, headers=headers).json()
        return data_matches, data_scorers
    except:
        return {}, {}

data_matches, data_scorers = carica_dati()

stats_squadre = {}
tot_gol, tot_partite_gironi = 0, 0

if 'matches' in data_matches and data_matches['matches']:
    for match in data_matches['matches']:
        if match['stage'] == 'GROUP_STAGE' and match['status'] == 'FINISHED':
            casa, ospite = match['homeTeam']['name'], match['awayTeam']['name']
            g_casa, g_ospite = match['score']['fullTime']['home'], match['score']['fullTime']['away']
            
            for sq in [casa, ospite]:
                if sq not in stats_squadre:
                    stats_squadre[sq] = {
                        'fatti': 0, 'subiti': 0, 'partite': 0, 
                        'clean_sheets': 0, 'ultimi_risultati': [],
                        'cronologia_gol': [],
                        'punti_pari_livello': 0, 'partite_pari_livello': 0
                    }
            
            stats_squadre[casa]['fatti'] += g_casa; stats_squadre[casa]['subiti'] += g_ospite; stats_squadre[casa]['partite'] += 1
            stats_squadre[ospite]['fatti'] += g_ospite; stats_squadre[ospite]['subiti'] += g_casa; stats_squadre[ospite]['partite'] += 1
            
            stats_squadre[casa]['cronologia_gol'].append(g_casa)
            stats_squadre[ospite]['cronologia_gol'].append(g_ospite)
            
            if g_ospite == 0: stats_squadre[casa]['clean_sheets'] += 1
            if g_casa == 0: stats_squadre[ospite]['clean_sheets'] += 1
            
            fascia_c = fasce_squadre.get(casa, 3)
            fascia_o = fasce_squadre.get(ospite, 3)
            if abs(fascia_c - fascia_o) <= 1:
                stats_squadre[casa]['partite_pari_livello'] += 1
                stats_squadre[ospite]['partite_pari_livello'] += 1
                if g_casa > g_ospite: stats_squadre[casa]['punti_pari_livello'] += 3
                elif g_casa == g_ospite:
                    stats_squadre[casa]['punti_pari_livello'] += 1
                    stats_squadre[ospite]['punti_pari_livello'] += 1
                else: stats_squadre[ospite]['punti_pari_livello'] += 3
            
            stats_squadre[casa]['ultimi_risultati'].append("W" if g_casa > g_ospite else ("D" if g_casa == g_ospite else "L"))
            stats_squadre[ospite]['ultimi_risultati'].append("W" if g_ospite > g_casa else ("D" if g_casa == g_ospite else "L"))
            tot_gol += (g_casa + g_ospite); tot_partite_gironi += 1

media_gol_torneo = (tot_gol / (tot_partite_gironi * 2)) if tot_partite_gironi > 0 else 1.2

dizionario_partite = {}
if 'matches' in data_matches and 'matches' in data_matches:
    for match in data_matches['matches']:
        if any(x in match['stage'].upper() for x in ['16', 'EIGHTH', 'ROUND']):
            c, o = match['homeTeam']['name'], match['awayTeam']['name']
            if c and o: dizionario_partite[f"{c} vs {o}"] = (c, o)

if dizionario_partite:
    # Selezione del match (senza label di testo sopra)
    scelta = st.selectbox("", list(dizionario_partite.keys()))
    casa, ospite = dizionario_partite[scelta]
    
    st.markdown("---")
    
    # Menu a tendina laterale per le varie sezioni richieste
    sezione = st.sidebar.radio(
        "Seleziona la sezione:",
        [
            "Impostazioni analisi",
            "Elaborazione pronostico",
            "Trend realizzativo (partite dei gironi)",
            "Info utili, logistica e palinsesto TV",
            "Dettaglio storico squadre"
        ]
    )

    # Inizializzazione variabili di calcolo necessarie a più sezioni
    if casa in stats_squadre and ospite in stats_squadre:
        gf_casa_media = stats_squadre[casa]['fatti']/stats_squadre[casa]['partite']
        gs_ospite_media = stats_squadre[ospite]['subiti']/stats_squadre[ospite]['partite']
        gf_ospite_media = stats_squadre[ospite]['fatti']/stats_squadre[ospite]['partite']
        gs_casa_media = stats_squadre[casa]['subiti']/stats_squadre[casa]['partite']

        # Stato di default per i valori se non modificati nella sezione "Impostazioni analisi"
        slider_c = st.session_state.get('slider_c', 1.0)
        slider_o = st.session_state.get('slider_o', 1.0)
        moltiplicatore_meteo = st.session_state.get('moltiplicatore_meteo', 1.0)
        nota_meteo = st.session_state.get('nota_meteo', "🏟️ Nessuna variazione climatica inserita.")

    # 1. IMPOSTAZIONI ANALISI
    if sezione == "Impostazioni analisi":
        st.markdown('<div class="section-header">⚙️ Impostazioni Analisi</div>', unsafe_allow_html=True)
        slider_c = st.slider(f"Stato di Forma / Motivazione {casa}", 0.5, 1.5, 1.0, 0.05, key='slider_c')
        slider_o = st.slider(f"Stato di Forma / Motivazione {ospite}", 0.5, 1.5, 1.0, 0.05, key='slider_o')
        
        st.markdown("##### 🌡️ Fattore Ambientale (Meteo)")
        meteo_selezionato = st.radio("Seleziona il clima stimato per il match:", 
                                     ["Meteo Standard / Condizionato (Stadio Chiuso)", "Caldo Estremo / Umido (Ondata di Calore USA 2026)", "Pioggia / Campo Pesante"])
        
        if meteo_selezionato == "Caldo Estremo / Umido (Ondata di Calore USA 2026)":
            st.session_state['moltiplicatore_meteo'] = 0.88
            st.session_state['nota_meteo'] = "⚠️ **Allerta Caldo:** Temperature previste sopra i 38°C (Ondata di calore estiva). Ritmo di gioco rallentato, favorevole a coperture 'Under'."
        elif meteo_selezionato == "Pioggia / Campo Pesante":
            st.session_state['moltiplicatore_meteo'] = 0.92
            st.session_state['nota_meteo'] = "🌧️ **Pioggia:** Campo scivoloso. Possibili errori difensivi ma calo della precisione balistica generale."
        else:
            st.session_state['moltiplicatore_meteo'] = 1.0
            st.session_state['nota_meteo'] = "🏟️ **Stadio Climatizzato:** Condizioni perfette al coperto. Nessuna interferenza sul modello matematico."
        
        st.info(st.session_state['nota_meteo'])
        st.success("Impostazioni caricate! Puoi cambiare sezione dal menu laterale.")

    # 2. ELABORAZIONE PRONOSTICO
    elif sezione == "Elaborazione pronostico":
        st.markdown('<div class="section-header">🔮 Elaborazione Pronostico</div>', unsafe_allow_html=True)
        
        lambda_casa = (gf_casa_media / media_gol_torneo) * (gs_ospite_media / media_gol_torneo) * media_gol_torneo
        lambda_ospite = (gf_ospite_media / media_gol_torneo) * (gs_casa_media / media_gol_torneo) * media_gol_torneo
        
        tiri_c, porta_c = dati_tiri_fbref.get(casa, (MEDIA_TIRI_TORNEO, MEDIA_PORTA_TORNEO))
        tiri_o, porta_o = dati_tiri_fbref.get(ospite, (MEDIA_TIRI_TORNEO, MEDIA_PORTA_TORNEO))
        
        prec_c = (porta_c / max(tiri_c, 1)) / (MEDIA_PORTA_TORNEO / MEDIA_TIRI_TORNEO)
        prec_o = (porta_o / max(tiri_o, 1)) / (MEDIA_PORTA_TORNEO / MEDIA_TIRI_TORNEO)
        
        spinta_tiri_casa = (tiri_c / MEDIA_TIRI_TORNEO) * 0.4
        spinta_tiri_ospite = (tiri_o / MEDIA_TIRI_TORNEO) * 0.4

        lambda_casa = max(lambda_casa * (0.8 + (prec_c - 1) * 0.2) + spinta_tiri_casa, 0.85) * slider_c * moltiplicatore_meteo
        lambda_ospite = max(lambda_ospite * (0.8 + (prec_o - 1) * 0.2) + spinta_tiri_ospite, 0.85) * slider_o * moltiplicatore_meteo
        
        prob_c = [poisson.pmf(i, lambda_casa) for i in range(8)]
        prob_o = [poisson.pmf(i, lambda_ospite) for i in range(8)]
        
        p_1, p_X, p_2 = 0, 0, 0
        risultati = {}
        prob_under_3_5 = 0.0
        
        for g_c in range(8):
            for g_o in range(8):
                p_comb = prob_c[g_c] * prob_o[g_o]
                tot_g = g_c + g_o
                if g_c > g_o: p_1 += p_comb
                elif g_c == g_o: p_X += p_comb
                else: p_2 += p_comb
                
                if tot_g <= 3: prob_under_3_5 += p_comb
                risultati[f"{g_c}-{g_o}"] = p_comb
        
        res_esatto = max(risultati, key=risultati.get)
        diff_percentuale = abs(p_1 - p_2)
        valore_equilibrio = int((1.0 - min(diff_percentuale * 2, 1.0)) * 100)
        
        if valore_equilibrio >= 75:
            indice_rischio = "🔴 ALTO RISCHIO"; colore_classe = "card-danger"
            motivazione_sintetica = f"Il modello mostra un equilibrio estremo ({valore_equilibrio}/100). Valori attesi vicini ({lambda_casa:.1f} vs {lambda_ospite:.1f}). Altissima probabilità di supplementari."
        elif valore_equilibrio >= 40:
            indice_rischio = "🟡 MEDIO RISCHIO"; colore_classe = "card-warning"
            favorita = casa if p_1 > p_2 else ospite
            motivazione_sintetica = f"Match controllato con leggero vantaggio per {favorita}. Equilibrio a quota {valore_equilibrio}/100. Consigliati mercati a copertura come Doppia Chance."
        else:
            indice_rischio = "🟢 BASSO RISCHIO"; colore_classe = "card-success"
            favorita = casa if p_1 > p_2 else ospite
            motivazione_sintetica = f"Match fortemente sbilanciato ({valore_equilibrio}/100 di equilibrio). Spinta balistica netta per {favorita}. Segno fisso consigliato."

        st.markdown(f'<div class="{colore_classe}">⚠️ <b>RISCHIO:</b> {indice_rischio}<br>💬 <b>MOTIVAZIONE:</b> {motivazione_sintetica}</div>', unsafe_allow_html=True)
        
        consigli_sicuri = []
        pct_under_3_5 = prob_under_3_5 * 100
        if pct_under_3_5 >= 85.0:
            consigli_sicuri.append(f"🎯 **Under 3.5 Match**: Probabilità del `{pct_under_3_5:.1f}%` (ritmo regolamentare gestito).")
        if (p_1 + p_X) * 100 >= 85.0:
            consigli_sicuri.append(f"🎯 **Doppia Chance 1X**: Probabilità del `{((p_1 + p_X) * 100):.1f}%` a favore di {casa}.")
        if (p_X + p_2) * 100 >= 85.0:
            consigli_sicuri.append(f"🎯 **Doppia Chance X2**: Probabilità del `{((p_X + p_2) * 100):.1f}%` a favore di {ospite}.")
            
        if consigli_sicuri:
            st.markdown('<div class="card-success">🔥 <b>CONSIGLI ALTA ACCURACY (85%+):</b><br>' + '<br>'.join(consigli_sicuri) + '</div>', unsafe_allow_html=True)

        st.write(f"**Bilanciamento delle Forze (Equilibrio Match):** `{valore_equilibrio} / 100`")
        st.progress(valore_equilibrio / 100)
        st.markdown(f'<div class="card-info">🎯 <b>RISULTATO IDENTIFICATO:</b> <span style="font-size:20px; font-weight:bold; color:#1E3A8A;">{res_esatto}</span></div>', unsafe_allow_html=True)
        
        tab_esiti, tab_distribuzione, tab_confronto = st.tabs(["📊 Esiti & Doppie", "📈 Top 5 Risultati", "⚔️ Attacco vs Difesa"])
        with tab_esiti:
            st.write(f"**Esito 1X2:** 1: `{p_1*100:.1f}%` | X: `{p_X*100:.1f}%` | 2: `{p_2*100:.1f}%`")
            st.write(f"**Doppia Chance:** 1X: `{(p_1+p_X)*100:.1f}%` | X2: `{(p_X+p_2)*100:.1f}%` | 12: `{(p_1+p_2)*100:.1f}%`")
        with tab_distribuzione:
            risultati_ordinati = sorted(risultati.items(), key=lambda x: x[1], reverse=True)[:5]
            df_risultati = pd.DataFrame(risultati_ordinati, columns=['Risultato Esatto', 'Probabilità'])
            df_risultati['Probabilità'] = df_risultati['Probabilità'].map(lambda x: f"{x*100:.1f}%")
            st.table(df_risultati)
        with tab_confronto:
            df_att_dif = pd.DataFrame({
                "Parametro Rilevato": ["Media Gol Fatti (Attacco)", "Media Gol Subiti (Difesa)", "Volume Tiri P/Partita"],
                casa: [f"{gf_casa_media:.2f}", f"{gs_casa_media:.2f}", f"{tiri_c}"],
                ospite: [f"{gf_ospite_media:.2f}", f"{gs_ospite_media:.2f}", f"{tiri_o}"]
            })
            st.table(df_att_dif)

    # 3. TREND REALIZZATIVO
    elif sezione == "Trend realizzativo (partite dei gironi)":
        st.markdown('<div class="section-header">📈 Trend Realizzativo (Partite dei Gironi)</div>', unsafe_allow_html=True)
        cronologia_c = stats_squadre[casa]['cronologia_gol']
        cronologia_o = stats_squadre[ospite]['cronologia_gol']
        
        lunghezza_max = max(len(cronologia_c), len(cronologia_o), 1)
        df_trend = pd.DataFrame({
            casa: cronologia_c + [np.nan]*(lunghezza_max - len(cronologia_c)),
            ospite: cronologia_o + [np.nan]*(lunghezza_max - len(cronologia_o))
        })
        df_trend.index = [f"Match {i+1}" for i in df_trend.index]
        st.line_chart(df_trend)

    # 4. INFO UTILI, LOGISTICA E PALINSESTO
    elif sezione == "Info utili, logistica e palinsesto TV":
        st.markdown('<div class="section-header">📺 Info Utili, Logistica & Palinsesto TV</div>', unsafe_allow_html=True)
        col_log1, col_log2 = st.columns(2)
        with col_log1:
            stadio_match = ottieni_stadio(casa, ospite)
            st.markdown(f"🏟️ **Sede dell'Incontro:** `{stadio_match}`")
            st.write("• *Nota logistica:* Gli stadi statunitensi dotati di coperture mobili attiveranno i sistemi di climatizzazione interni per contrastare l'estrema ondata di umidità estiva.")
        with col_log2:
            st.markdown("📺 **Dove vedere la partita in TV / Streaming:**")
            st.write("• **Italia:** Diretta esclusiva sui canali **Rai Sport / Rai 1** e in streaming gratuito su **RaiPlay**.")
            st.write("• **Internazionale:** Distribuzione ufficiale affidata a FOX, FS1 (Stati Uniti) e BBC/ITV (UK).")

    # 5. DETTAGLIO STORICO SQUADRE
    elif sezione == "Dettaglio storico squadre":
        st.markdown('<div class="section-header">📊 Dettaglio Storico Squadre</div>', unsafe_allow_html=True)
        t_casa, t_ospite = st.columns(2)
        for sq, colonna, ruolo in [(casa, t_casa, "CASA"), (ospite, t_ospite, "OSPITE")]:
            dati = stats_squadre[sq]
            with colonna:
                st.markdown(f"#### 🏆 {sq} ({ruolo})")
                st.write(f"• **Forma gironi:** {'-'.join(dati['ultimi_risultati'])} | **Clean Sheets:** {dati['clean_sheets']}")
                if dati['partite_pari_livello'] > 0:
                    media_punti_pari = dati['punti_pari_livello'] / dati['partite_pari_livello']
                    st.write(f"• **Rendimento contro Big:** `Media {media_punti_pari:.2f} Punti` ({dati['partite_pari_livello']} match)")
                else:
                    st.write(f"• **Rendimento contro Big:** `Nessun match disputato`")
else:
    st.error("Nessun match degli ottavi trovato al momento.")
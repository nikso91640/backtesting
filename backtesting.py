import yfinance as yf
import pandas as pd
from dateutil import relativedelta
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st

yf.pdr_override()

# Définition de fréquences
freqs = [1, 3, 6, 12]
# Création d'un dictionnaire associant les fréquences à des couleurs spécifiques
frequency_colors = {1: 'red', 3: 'green', 6: 'blue', 12: 'purple'}  # Ajoutez d'autres fréquences et couleurs si nécessaire

# Création du graphique avec Plotly
fig = go.Figure()

@st.cache
def calculate_cumulative_returns(ticker, start_year, end_year, initial_amount, recurring_amount):
    total_recurring_investments = 0

    start_date = datetime(int(start_year), 1, 1)
    end_date = datetime(int(end_year), 1, 1)

    next_end_date = end_date + relativedelta.relativedelta(months=1)

    resultats = {}  # Un dictionnaire pour stocker les résultats de toutes les fréquences

    data = yf.download(ticker, start=start_date, end=next_end_date, interval="1mo")

    years_difference = data.index[-1].year - data.index[0].year
    months_count = years_difference * 12

    valeur_investissement_lumpsum = []
    valeur_investissement_lumpsum.append(initial_amount + (months_count * recurring_amount))

    for frequency in [1, 3, 6, 12]:  # Boucle pour les fréquences de 1 mois à 12 mois

        recurring_amount = recurring_amount * frequency

        montant_final_actuel = 0

        frequency_name = f'{frequency}MS'

        valeurs_investissements_cumulatives = [initial_amount]

        # Créez une liste pour stocker les investissements initiaux + récurrents cumulatifs
        investissements_initiaux_recurrents_cumulatifs = [initial_amount]

        color = frequency_colors.get(frequency, 'black')  # 'black' sera la couleur par défaut si la fréquence n'a pas de couleur spécifique définie
        # On crée une série de dates avec la fréquence voulue
        dates = pd.date_range(start=data.index[0], end=data.index[-1], freq=frequency_name)

        # On crée un DataFrame avec les dates
        dates = pd.DataFrame({'Date': dates})
        dates['Date'] = pd.to_datetime(dates['Date'])

        # On récupère la colonne 'Adj Close' de data et on l'associe aux dates correspondantes
        adj_close = data['Adj Close'].reset_index()  # Reset l'index pour avoir la colonne 'Date'
        merged_data = pd.merge(dates, adj_close, on='Date', how='left')  # Fusionne les DataFrames sur la colonne 'Date'

        # Montant initial d'investissement
        investissement = initial_amount

        # Le PRU (Prix de Revient Unitaire) est initialisé à la valeur de clôture du premier jour
        # si l'investissement est supérieur ou égal à ce montant, sinon, il est défini à zéro.
        PRU = merged_data.iloc[0]['Adj Close'] if investissement >= merged_data.iloc[0]['Adj Close'] else 0

        # Les liquidités sont calculées comme le reste de l'investissement initial divisé
        # par le prix de clôture du premier jour.
        liquidites = investissement % merged_data.iloc[0]['Adj Close']

        # Le nombre d'ETF achetés initialement est calculé en divisant l'investissement initial par le PRU.
        if PRU != 0:
            nombre_etf = investissement // PRU
        else:
            nombre_etf = 0

        # Le montant final est calculé comme le produit du PRU et du nombre d'ETF détenus,
        # plus les liquidités restantes.
        montant_final = merged_data.iloc[0]['Adj Close'] * nombre_etf + liquidites

        # Le pourcentage d'évolution est initialisé à zéro car il n'y a pas encore eu d'évolution.
        pourcentage_evolution = 0

        # Montant total investi avant un nouvel achat est calculé en soustrayant les liquidités
        # actuelles de l'investissement initial. Cela représente le montant total investi
        # dans des ETF avant l'achat actuel.
        montant_total_investi_avant_achat = investissement - liquidites

        nombre_etf_lumpsum = valeur_investissement_lumpsum[0] // merged_data.iloc[0]['Adj Close']
        liquidites_lumpsum = valeur_investissement_lumpsum[0] % merged_data.iloc[0]['Adj Close']

        # Boucle pour traiter les dates à partir de la deuxième date
        for index, date in enumerate(merged_data['Date'][1:], start=1):

            # Calcul de l'investissement initial + récurrents cumulatifs pour la courbe "total des versements"
            investissements_cumulatifs = investissements_initiaux_recurrents_cumulatifs[-1] + recurring_amount
            investissements_initiaux_recurrents_cumulatifs.append(investissements_cumulatifs)

            # Augmenter l'investissement récurrent
            investissement += recurring_amount
            liquidites += recurring_amount

            # Calcul du nombre d'ETF achetés à la date actuelle
            nombre_etf_achetes = liquidites // merged_data.iloc[index]['Adj Close']

            # Calcul du montant total investi à la date actuelle
            montant_total_investi = nombre_etf_achetes * merged_data.iloc[index]['Adj Close']

            # Soustraire le montant investi à la liquidité
            liquidites -= montant_total_investi

            # Mettre à jour le nombre total d'ETF détenus
            nombre_etf += nombre_etf_achetes

            if nombre_etf_achetes > 0:

                # Montant investi à la date actuelle
                montant_investi_actuel = montant_total_investi
                # Mise à jour du montant total investi avant l'achat actuel en ajoutant le montant investi actuel
                montant_total_investi_avant_achat = montant_total_investi_avant_achat + montant_investi_actuel
                # Calcul du nouveau PRU
                PRU = (montant_total_investi_avant_achat) / (nombre_etf)

                montant_final_actuel = merged_data.iloc[index]['Adj Close'] * nombre_etf + liquidites
                # Ajoutez la valeur cumulée des investissements à la liste
                valeurs_investissements_cumulatives.append(montant_final_actuel)
            else:
                # Ajoutez la valeur cumulée des investissements à la liste
                montant_final_actuel = montant_final_actuel + recurring_amount
                valeurs_investissements_cumulatives.append(montant_final_actuel)

            if (frequency == 12):
                valeur_investissement_lumpsum.append(
                    nombre_etf_lumpsum * merged_data.iloc[index]['Adj Close'])

        # Calcul du montant final
        montant_final = (merged_data.iloc[index]['Adj Close'] * nombre_etf) + liquidites

        # Calcul du pourcentage d'évolution par rapport à l'investissement initial
        pourcentage_evolution = ((montant_final / investissement) - 1) * 100

        total_investissements_recurrents = index * recurring_amount

        # On réinitialise le montant récurrent en fonction de la freq
        recurring_amount = recurring_amount // frequency

        fig.add_trace(go.Scatter(x=merged_data['Date'], y=valeurs_investissements_cumulatives,
                mode='markers+lines', name=f'Fréquence : {frequency} mois',
                marker=dict(color=color, symbol='circle', size=4)))
        
        # Stocker les résultats dans le dictionnaire avec la clé de la fréquence correspondante
        resultats[f'{frequency}mo'] = {
            'montant_final': montant_final,
            'pourcentage_evolution': pourcentage_evolution,
            'PRU': PRU,
            'date_first_invest': merged_data['Date'].iloc[0].strftime("%Y-%m-%d"),
            'date_last_invest': merged_data['Date'].iloc[index].strftime("%Y-%m-%d"),
            'nombre_investissement': index + 1,
            'total_investissement': total_investissements_recurrents + initial_amount
        }

    meilleure_frequence = max(resultats, key=lambda f: resultats[f]['pourcentage_evolution'])
    meilleur_resultat = resultats[meilleure_frequence]
    # Accédez au montant final de la meilleure fréquence
    montant_final_max = resultats[meilleure_frequence]['montant_final']

    lumpSum = {
        'investissement': initial_amount + (months_count * recurring_amount),
        'valeur_finale_investissement': valeur_investissement_lumpsum + liquidites_lumpsum,
        'interets': lumpSum['valeur_finale_investissement'] - lumpSum['investissement'],
        'evolution': ((lumpSum['valeur_finale_investissement / lumpSum['investissement']) - 1) * 100
    }

    fig.add_trace(go.Scatter(x=dates['Date'], y=investissements_initiaux_recurrents_cumulatifs,
                mode='markers+lines', name='Total des versements',
                marker=dict(color='black', symbol='circle', size=4)))
    fig.add_trace(go.Scatter(x=dates['Date'], y=lumpSum['valeur_finale_investissement'],
                mode='markers+lines', name='Lump Sum',
                marker=dict(color='orange', symbol='circle', size=4)))
    
    return resultats, meilleure_frequence, meilleur_resultat, years_difference, montant_final_max, lumpSum


# Fonction principale pour exécuter le code Streamlit
def main():
    st.title("Analyse investissement - DCA vs Lump Sum")

    # Création des widgets d'entrée dans Streamlit
    ticker = st.text_input("Entrez le ticker Yahoo Finance (par exemple 'CW8.PA') : ")
    date_debut = st.number_input("Entrez l'année de début : ", min_value=1900, max_value=datetime.now().year)
    date_fin = st.number_input("Entrez l'année de fin : ", min_value=date_debut, max_value=datetime.now().year)
    montant_initial = st.number_input("Entrez le montant initial en euros : ", min_value=1)
    montant_recurrent = st.number_input("Entrez le montant récurrent : ", min_value=1)

    if st.button("Analyser"):
        # Calcul des rendements cumulatifs
        resultats = calculate_cumulative_returns(ticker, date_debut, date_fin, montant_initial, montant_recurrent)

        meilleure_frequence = resultats[1]
        meilleur_resultat = resultats[2]
        years_difference = resultats[3]
        montant_final_max = resultats[4]
        interets = montant_final_max - resultats[0][meilleure_frequence]['total_investissement']

        # Affichage des informations récapitulatives
        st.write(f"ETF : {ticker}")
        st.write(f"Durée d'investissement : {years_difference} ans")
        st.write(f"Total des investissements (initial + récurrents): {resultats[0][meilleure_frequence]['total_investissement']:.2f} €")

        # Affichage des résultats finaux DCA
        st.write('\n----------- DCA --------------')
        st.write(f"Meilleure fréquence : {meilleure_frequence}")
        st.write(f"Montant épargné : {resultats[0][meilleure_frequence]['total_investissement']:.2f} €")
        st.write(f"Montant final : {montant_final_max:.2f} €")
        st.write(f"Intérêts composés : {interets:.2f} €")
        st.write(f"Pourcentage d'évolution : {meilleur_resultat['pourcentage_evolution']:.2f} %")
        st.write(f"CAGR : {((((resultats[0][meilleure_frequence]['montant_final'] / resultats[0][meilleure_frequence]['total_investissement'])) ** (1 / years_difference)) - 1) *100:.2f} %")

        # Affichage des résultats finaux Lump Sum
        st.write('\n----------- LUMP SUM --------------')
        st.write(f"Montant unique épargné : {lumpSum['investissement']} €")
        st.write(f"Montant final : {lumpSum['valeur_finale_investissement']} €")
        st.write(f"Intérêts composés : {lumpSum} €")
        st.write(f"Pourcentage d'évolution : {} %")
        st.write(f"CAGR : {((((lumpSum['valeur_finale_investissement'] / lumpSum['investissement'])) ** (1 / years_difference)) - 1) *100:.2f} %")


        # Mise en forme du titre et des axes
        fig.update_layout(title=f'Évolution de l'investissement -{yf.Ticker(ticker).info['shortName']}',
                          xaxis_title='Date',
                          yaxis_title='Montant (en euros)')

        # Affichage du graphique avec Streamlit
        st.plotly_chart(fig)
        
if __name__ == "__main__":
    main()

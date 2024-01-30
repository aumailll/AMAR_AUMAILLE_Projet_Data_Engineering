"""
Ce script Python utilise le framework Dash pour créer un tableau de bord interactif
afin d'étudier le classement des animes. Les données sont extraites d'une base de données
MongoDB qui est préalablement alimentée à l'aide d'une spider Scrapy collectant des informations
sur les animes depuis le site MyAnimeList.net.

Le tableau de bord comprend les sections suivantes :
1. Liens vers les 10 animes les mieux notés avec possibilité de navigation.
2. Frise permettant de sélectionner une tranche d'animes en fonction de leur rang.
3. Barre de recherche pour trouver des informations détaillées sur un anime spécifique.
4. Sections avec des graphiques interactifs :
    - Histogramme des studios les plus productifs.
    - Histogramme du statut des animes.
    - Diagramme circulaire des genres les plus populaires.
    - Histogramme du nombre d'épisodes.

Le tableau de bord est stylisé avec Bootstrap pour un aspect visuel amélioré.

Fonctions principales :
----------------------

1. `update_graph(selected_range)`: 
   - Description: Fonction de callback pour mettre à jour les graphiques en fonction de la tranche sélectionnée.
   - Paramètres:
     - `selected_range` (list): Tranche d'animes sélectionnée.
   - Retourne:
     - Graphiques actualisés et texte de sortie.

2. `search_anime_details(n_clicks, search_input)`: 
   - Description: Fonction de callback pour gérer la recherche et afficher les détails de l'anime recherché.
   - Paramètres:
     - `n_clicks` (int): Nombre de clics sur le bouton de recherche.
     - `search_input` (str): Terme de recherche.
   - Retourne:
     - Fiche détaillée de l'anime ou message d'erreur.

3. Autres fonctions auxiliaires pour le traitement des données et le nettoyage du texte.
"""

from dash import dcc, html
import dash
from dash.dependencies import Input, Output, State
import pandas as pd
from pymongo import MongoClient
import os   # Connexion à la base de données MongoDB

URI = os.getenv("MONGO_URI")
client = MongoClient(URI)
db = client['anime_vf2']
collection = db['collect_anime']

# Chargement des données depuis la base de données MongoDB
cursor = collection.find({})
df = pd.DataFrame(list(cursor))

# Ajout d'une feuille de style de Bootstrap
external_stylesheets = ['https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css', 'style.css']

# Création de l'application Dash
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


# Mise en page de l'application
app.layout = html.Div([
    html.Br(),
    # Titre : 
    html.H1("Étude du classement des animes", style={'textAlign': 'center', 'fontSize': '3em'}),

    html.Br(),
    html.Br(),

    # Sélection des 10 premiers liens vers les Animes les mieux notés
    html.H2("\n\nLiens vers les Animes les mieux notés", className="my-heading"),
    dcc.Markdown(id='top-animes-links', className="mb-4"),

    # Frise permettant de sélectionner la tranche d'anime en fonction de leur rang
    html.Div([
        html.Label("Sélectionnez une tranche d'animes en fonction du rang :", className="my-3"),
        dcc.RangeSlider(
            id='range-slider',
            marks={i: str(i) for i in range(1, 300, 50)},
            min=1,
            max=300,
            step=1,
            value=[1, 50],
            className="mb-4"
        ),
        html.Div(id='selected-range-output', className="my-3"),
    ], className="border rounded p-3"),

    # Barre de recherche permettant d'afficher la fiche technique de l'anime
    html.Div([
        html.Label("Rechercher un anime :", className="my-3", style={'font-size': '1.5em', 'text-align': 'center'}),
        dcc.Input(id='search-input', type='text', value='', className="mb-4", style={'width': '60%', 'margin': '0 auto', 'display': 'block'}),
        html.Button('Rechercher', id='search-button', n_clicks=0, className="btn btn-primary", style={'display': 'block', 'margin': '0 auto'}),
    ], className="border rounded p-3"),

    # Emplacement pour afficher la page détaillée de l'anime sélectionné
    dcc.Location(id='url', refresh=False),
    html.Div(id='anime-details-page', className="my-4"),

    # Histogramme des studios les plus productifs
    html.H2("\n\nHistogramme des studios les plus productifs", className="my-heading"),
    dcc.Graph(id='top-studios', className="mb-4"),

    # Histogramme sur le statut
    html.H2("\n\nHistogramme du statut", className="my-heading"),
    dcc.Graph(id='anime-status', className="mb-4"),

    # Diagramme circulaire des genres les plus populaires
    html.H2("\n\nDiagramme ciculaire des genres les plus populaires", className="my-heading"),
    dcc.Graph(id='top-genres', className="mb-4"),

    # Histogramme du nombre d'épisodes
    html.H2("\n\nHistogramme du nombre d'épisodes", className="my-heading"),
    dcc.Graph(id='episode-histogram', className="mb-4"),
], className="container-fluid")

# Callback pour mettre à jour les graphiques et le texte de sortie en fonction de la tranche sélectionnée
@app.callback(
    [Output('top-studios', 'figure'),
     Output('anime-status', 'figure'),
     Output('top-animes-links', 'children'),
     Output('top-genres', 'figure'),
     Output('episode-histogram', 'figure'),
     Output('selected-range-output', 'children')],
    [Input('range-slider', 'value')]
)
def update_graph(selected_range):
    # Ligne permettant d'isoler la tranche sélectionnée du dataframe
    selected_df = df[(df['rank'].astype(int) >= selected_range[0]) & (df['rank'].astype(int) <= selected_range[1])]

    # Liens vers les animes les mieux notés
    top_animes_links = [f"{i+1}. [{title}]({link}) - Score: {score}\n" for i, (title, link, score) in enumerate(zip(selected_df.head(10)['title'], selected_df.head(10)['link'], selected_df.head(10)['score']))]

    # Studios les plus productifs
    top_studios_figure = {
        'data': [
            {'x': selected_df['studio'].explode().value_counts().index, 'y': selected_df['studio'].explode().value_counts().values, 'type': 'bar', 'name': 'Nombre d\'animes'},
        ],
        'layout': {
            'title': 'Studios les plus productifs',
            'xaxis': {'title': 'Studio'},
            'yaxis': {'title': 'Nombre d\'animes produits'}
        }
    }

    # Statut
    anime_status_figure = {
        'data': [
            {'x': selected_df['statut'].value_counts().index, 'y': selected_df['statut'].value_counts().values, 'type': 'bar', 'name': 'Nombre d\'animes'},
        ],
        'layout': {
            'title': 'Distribution des Animes en fonction du Statut',
            'xaxis': {'title': 'Statut'},
            'yaxis': {'title': 'Nombre d\'animes'}
        }
    }

    # Genres les plus populaires
    top_genres_figure = {
        'data': [
            {
                'labels': selected_df['genres_ET_themes'].explode().value_counts().index,
                'values': selected_df['genres_ET_themes'].explode().value_counts().values,
                'type': 'pie',
                'name': 'Nombre d\'animes'
            },
        ],
        'layout': {
            'title': 'Genres les plus populaires',
        }
    }

    # Nombre d'Épisodes
    episode_histogram_figure = {
        'data': [
            {
                'x': selected_df['title'],
                'y': selected_df['episodes'],
                'type': 'bar',
                'name': 'Nombre d\'épisodes'
            },
        ],
        'layout': {
            'title': "Histogramme du Nombre d'Épisodes",
            'xaxis': {'title': 'Anime'},
            'yaxis': {'title': 'Nombre d\'épisodes'}
        }
    }

    selected_range_text = f"Animes sélectionnés : {selected_range[0]} à {selected_range[1]}"

    return top_studios_figure, anime_status_figure, top_animes_links, top_genres_figure, episode_histogram_figure, selected_range_text

# Callback pour gérer la recherche et afficher la fiche détaillée de l'anime sélectionné
@app.callback(
    Output('anime-details-page', 'children'),
    [Input('search-button', 'n_clicks')],
    [State('search-input', 'value')]
)
def search_anime_details(n_clicks, search_input):
    if n_clicks > 0 and search_input:
        # Recherche de l'anime dans la base de données
        anime_details = collection.find_one({'title': {'$regex': f'.*{search_input}.*', '$options': 'i'}})

        if anime_details:
            return html.Div([
                html.H2(anime_details['title']),
                html.P(f"Score: {anime_details['score']}"),
                html.P(f"Studios: {', '.join(anime_details['studio']).replace(',', '')}"),
                html.P(f"Genres et thèmes: {', '.join(anime_details['genres_ET_themes']).replace(',', '')}"),
                html.P(f"Statut: {anime_details['statut']}"),
                html.P(f"Nombre d'épisodes: {anime_details['episodes']}"),
            ])
        else:
            return html.P("Aucun résultat trouvé.")
    else:
        return html.Div()

# Exécution de l'application
if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')

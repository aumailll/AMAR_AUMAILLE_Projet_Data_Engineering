"""
Ce script Python est destiné à être utilisé comme une spider pour le framework de scraping web Scrapy.
Il a pour objectif de collecter des informations sur les animes à partir du site MyAnimeList.net, en particulier les animes les mieux notés.

Fonctions et Classes:
----------------------

1. `clean_text(text)`: 
   - Description: Fonction utilitaire pour nettoyer le texte en supprimant les espaces et les caractères indésirables.
   - Paramètres:
     - `text` (str): Texte à nettoyer.
   - Retourne:
     - Texte nettoyé.

2. `MyAnimeListSpider(scrapy.Spider)`:
   - Description: Classe représentant la spider pour collecter les informations sur les animes depuis MyAnimeList.net.
   - Attributs de classe:
     - `name`: Nom de la spider.
     - `allowed_domains`: Liste des domaines autorisés.
     - `start_urls`: Liste des URLs de départ.
   - Méthodes:
     - `__init__(self, *args, **kwargs)`: Initialise la spider, établit une connexion à la base de données MongoDB.
     - `parse(self, response)`: Méthode de parsing pour extraire les informations de base des pages listant les animes.
     - `parse_anime_page(self, response)`: Méthode de parsing pour extraire des informations détaillées à partir des pages d'anime individuelles.
     - `closed(self, reason)`: Méthode appelée lorsque la spider est fermée pour trier et afficher les résultats, et les stocker dans une base de données MongoDB.
"""

import scrapy
from pymongo import MongoClient
import os
import pymongo 

# Remarque : cette fonction ne fonctionne pas pour les listes
def clean_text(text):
    return ' '.join(text.split()).strip(' \n[]')


class MyAnimeListSpider(scrapy.Spider):
    name = 'anime'
    allowed_domains = ['myanimelist.net']
    start_urls = [
        'https://myanimelist.net/topanime.php',
        'https://myanimelist.net/topanime.php?limit=50',
        'https://myanimelist.net/topanime.php?limit=100',
        'https://myanimelist.net/topanime.php?limit=150',
        'https://myanimelist.net/topanime.php?limit=200',
        'https://myanimelist.net/topanime.php?limit=250',
    ]
    
    def __init__(self, *args, **kwargs):
        super(MyAnimeListSpider, self).__init__(*args, **kwargs)
        self.client = pymongo.MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client['anime_vf2']
        self.collection = self.db['collect_anime']
        


    results = []  # Ajout d'une liste pour stocker les résultats
    

    def parse(self, response):
        animes = response.css('.ranking-list')

        # On extrait les informations que l'on souhaite : rang, titre, lien web, score
        # On en profite pour corriger le format du titre qui était initialement "Anime: Titre" pour "Titre"
        for anime in animes:
            item = {}
            item['rank'] = anime.css('.rank span::text').get().strip()

            title_element = anime.css('td.title a')
            item['title'] = title_element.css('img::attr(alt)').get()
            item['title'] = item['title'].replace('Anime: ', '')

            item['link'] = title_element.css('::attr(href)').get()

            #score_star = anime.css('.icon-score-star.on::text').get()
            score_label = anime.css('.score-label::text').get()
            item['score'] = f"{score_label}"
            yield scrapy.Request(url=item['link'], callback=self.parse_anime_page, meta={'item': item})


    def parse_anime_page(self, response):
        # On extrait les informations supplémentaires que l'on souhaite depuis la page de l'anime
        # Avec en particulier : nombre d'épisodes, statut, studio de production, producteurs, type (démographie), genre et thème.
        item = response.meta['item']

        item['episodes'] = clean_text(response.xpath('//span[text()="Episodes:"]/following-sibling::text()').get())
        item['statut'] = clean_text(response.xpath('//span[text()="Status:"]/following-sibling::text()').get())

        item['studio'] = response.css('span:contains("Studios:") + a::text').getall()
        item['producteurs'] = response.css('span:contains("Producers:") + a::text').getall()

        blatest = response.css('span:contains("Genres:") + span[itemprop="genre"]::text , span[itemprop="genre"]::text').getall()

        demographic = response.css('div.spaceit_pad span.dark_text:contains("Demographic:") + span[itemprop="genre"] + a::text').get()
        item['type'] = demographic

        item['genres_ET_themes'] = [g for g in blatest if g not in [demographic]]
        self.results.append(item)


    def closed(self, reason):
        # Une fois que la spider est fermée, on trie les résultats par le champ 'rank' et on les affiche (triés)
        self.logger.info("-----------------------Spider fermée: tri des résultats en fonction du 'rank'.-----------------------")
        self.results.sort(key=lambda x: int(x['rank']))
        for result in self.results:
            self.logger.info(result)
        
        for result in self.results:
            self.collection.insert_one({
                'rank': result['rank'],
                'title': result['title'],
                'link': result['link'],
                'score': result['score'],
                'episodes': result['episodes'],
                'statut': result['statut'],
                'studio': result['studio'],
                'producteurs': result['producteurs'],
                'type': result['type'],
                'genres_ET_themes': result['genres_ET_themes'],
            })

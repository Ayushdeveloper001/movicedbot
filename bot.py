
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultPhoto, InputMediaPhoto, Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, InlineQueryHandler, Filters
import random
import emoji
from tmdbv3api import Movie
import requests
import json
import datetime
import logging
from collections import OrderedDict
import tmdbsimple as tmdb  # For TMDB API interactions
import matplotlib.pyplot as plt
import io
import re
import locale
from urllib.parse import quote
import numpy as np  # Import NumPy for calculations
BOT_TOKEN = ''

command_descriptions = {
    'help': "🎬 Watch your favourite shows and movies with this open source streaming bot.\n\nUse /movie moviename command to Search Movies!\n\nUse /series seriesname command to Search Series! (Do not write Season or Episode number, you should be able to choose it in the external link)\n\n<b>Useful Commands:</b>\n\nhelp - Streaming Bot \ncopyright - Disclaimer Notice \nDMCA - Copyright Reporting \nstart - About Moviced \nfaq - Common Questions \ndev - Source Code",
    'copyright': "Moviced does not host any files, it merely links to 3rd party services. Legal issues should be taken up with the file hosts and providers. Moviced is not responsible for any media files shown by the video providers.",
    'dev': "We believe in transparency. Therefore, we've made our bot open-source so that our users can inspect the source code, understand its functionality, and how it handles their data.\n\nFor developers, here is our <a href='https://drive.google.com/file/d/15JYITtcEssy9Hif2LHbmkiyoDw1aXXAo/view?usp=sharing'>View Source Code</a>\n\nWe do not store or sell users' data in any form. Our policy strictly prohibits such practices.",
    'DMCA': "Welcome to the MovicedBot's DMCA! We respect intellectual property rights and want to address any copyright concerns swiftly. If you believe your copyrighted work has been improperly used on our platform, please send a detailed DMCA notice to the email below. Please include a description of the copyrighted material, your contact details, and a statement of good faith belief. We're committed to resolving these matters promptly and appreciate your cooperation in keeping MovicedBot a place that respects creativity and copyrights.\n\n✉️ religiondotscience@gmail.com",
    'start': "<b>About Moviced</b>\n\nMoviced is a Bot that searches the internet for streams. The team aims for a mostly minimalistic approach to consuming content.\n\nUse /movie moviename command to Search Movies!\n\nUse /series seriesname to Search Series! (Do not write Season or Episode number)\n\nUse /recommend to Find random underrated movies!",
    'faq': "<b>Common questions</b>\n\n<b>1. Where does the content come from?</b>\n\nMovicedBot does not host any content. When you click on something to watch, the internet is searched for the selected media (On the loading screen and in the 'video sources' tab you can see which source you're using). Media never gets uploaded by Moviced, everything is through this searching mechanism.\n\n<b>2. Where can I request a show or movie?</b>\n\nIt's not possible to request a show or movie, Moviced does not manage any content. All content is viewed through sources on the internet.\n\n<b>3. The search results display the show or movie, why can't I play it?</b>\n\nOur search results are powered by The Movie Database (TMDB) and display regardless of whether our sources actually have the content."
}

updater = Updater(BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

TMDB_API_KEY = ''

tmdb.API_KEY = ''

TMDB_SEARCH_URL = 'https://api.themoviedb.org/3/search/movie?'

with open('movies_data.json', 'r') as file:
    movie_data = json.load(file)

def random_movie(update, context):
    random_movie_entry = random.choice(movie_data)
    film_info = random_movie_entry.get('film')
    if not film_info:
        update.message.reply_text('Movie information not found in the selected entry.')
        return

    artworks = film_info.get('artworks', [])
    cover_horizontal_image_url = next((artwork['image_url'] for artwork in artworks if artwork['format'] == 'cover_artwork_horizontal'), None)
    still_url = film_info.get('still_url', None)
    genred = film_info.get('genres', [])
    if not cover_horizontal_image_url:
        cover_horizontal_image_url = still_url

    message = f"<b>{film_info['title'].upper()} | {film_info['year']}</b>\n\n"
    message += f"<b>Genres:</b> {', '.join(genred)}\n\n"
    message += f"{film_info['short_synopsis']}\n\n"
    message += f"<b>⭐ Rating: <span class='tg-spoiler'>{film_info['average_rating_out_of_ten']}</span></b>\n\n"
    message += "Copyright Legality:\n/copyright@MoviedBot"

    cover_horizontal_image_url_cleaned = cover_horizontal_image_url.split('?')[0]

    try:
        keyboard = [
            [
                telegram.InlineKeyboardButton("Watch Trailer", url=f"https://elfin-peridot-orbit.glitch.me/source?source={film_info['trailer_url']}"),
                telegram.InlineKeyboardButton("Reload ⟳", callback_data='reload_random')
            ]
        ]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)

        loading_message = context.bot.send_message(chat_id=update.effective_chat.id, text="Loading...")

        sent_message = context.bot.send_photo(chat_id=update.effective_chat.id, photo=cover_horizontal_image_url_cleaned, caption=message, reply_markup=reply_markup, parse_mode='html')
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_message.message_id)

        context.user_data['last_recommendation_message'] = sent_message.message_id

        context.user_data['last_recommendation_film_info'] = film_info

    except telegram.error.BadRequest as e:
        print(f"Error sending photo with cover_horizontal_image_url: {e}")
        send_alternative_image(update, context, message, still_url, film_info)  # Sending alternative image and handling reload
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_message.message_id)

def send_alternative_image(update, context, message, image_url, film_info):
    try:
        keyboard = [
            [
                telegram.InlineKeyboardButton("Watch Trailer", url=f"https://elfin-peridot-orbit.glitch.me/source?source={film_info['trailer_url']}"),
                telegram.InlineKeyboardButton("Reload ⟳", callback_data='reload_random')
            ]
        ]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)

        sent_message = context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url, caption=message, reply_markup=reply_markup, parse_mode='html')


        context.user_data['last_recommendation_message'] = sent_message.message_id
        context.user_data['last_recommendation_film_info'] = film_info

    except telegram.error.BadRequest as e:
        print(f"Error sending photo with image_url: {e}")
        update.message.reply_text("Failed to load the image.")



def reload_random_movie(update, context):
    query = update.callback_query
    query.answer()

    last_message_id = context.user_data.get('last_recommendation_message')
    if last_message_id:
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)

    if 'last_recommendation_film_info' in context.user_data:
        context.user_data.pop('last_recommendation_film_info')
        random_movie(update, context)
    else:
        random_movie(update, context)

dispatcher.add_handler(CallbackQueryHandler(reload_random_movie, pattern='reload_random'))
def recommend(update, context):
    keyboard = [
        [
            InlineKeyboardButton("Random", callback_data='random'),
            InlineKeyboardButton("Choose a genre", callback_data='genres')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Choose an option:', reply_markup=reply_markup)

def genres(update, context):
    genres = [
        'Romance', 'Comedy', 'Animation', 'Crime', 'Drama', 'Sci-Fi', 'War', 'Western', 'Adventure',
        'Silent', 'Short', 'Horror', 'History', 'Biography', 'Film noir', 'Action',
        'Cult', 'Thriller', 'Fantasy', 'Documentary', 'Avant-Garde', 'Mystery'
    ]

    keyboard = [genres[i:i + 3] for i in range(0, len(genres), 3)]
    keyboard = [[InlineKeyboardButton(genre, callback_data=f'genre_{genre}') for genre in row] for row in keyboard]

    reply_markup = InlineKeyboardMarkup(keyboard)
    if context.user_data.get('genre_message_id'):
        messaged = update.callback_query.edit_message_text('Choose a genre:', reply_markup=reply_markup)
        context.user_data['genre_list_message_id'] = messaged.message_id
    else:
        message = context.bot.send_message(chat_id=update.effective_chat.id, text='Choose a genre:', reply_markup=reply_markup)
        context.user_data['genre_message_id'] = message.message_id

def button(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'random':
        random_movie(update, context)
    elif query.data == 'genres':
        genres(update, context)
    elif query.data == 'back':
        genres(update, context)
    elif query.data.startswith('genre_'):
        genre = query.data.split('_')[1]
        movies_by_genre = [movie for movie in movie_data if 'film' in movie and genre in movie.get('film', {}).get('genres', [])]
        if movies_by_genre:
            chosen_movie = random.choice(movies_by_genre)
            film_info = chosen_movie['film']
            if not film_info:
                update.message.reply_text('Movie information not found in the selected entry.')
                return

            artworks = film_info.get('artworks', [])
            cover_horizontal_image_url = next((artwork['image_url'] for artwork in artworks if artwork['format'] == 'cover_artwork_horizontal'), None)
            still_url = film_info.get('still_url', None)
            genred = film_info.get('genres', [])
            if not cover_horizontal_image_url:
                cover_horizontal_image_url = still_url

            message = f"<b>{film_info['title'].upper()} | {film_info['year']}</b>\n\n"
            message += f"<b>Genres:</b> {', '.join(genred)}\n\n"
            message += f"{film_info['short_synopsis']}\n\n"
            message += f"<b>⭐ Rating: <span class='tg-spoiler'>{film_info['average_rating_out_of_ten']}</span></b>\n\n"
            message += "Copyright Legality:\n/copyright@MovicedBot"

            cover_horizontal_image_url_cleaned = cover_horizontal_image_url.split('?')[0]
            if not cover_horizontal_image_url_cleaned:
                cover_horizontal_image_url_cleaned = still_url
            try:
                keyboard = [
                    [

                        telegram.InlineKeyboardButton("Watch Trailer", url=film_info['trailer_url'])
                    ]
                ]

                reply_markup = telegram.InlineKeyboardMarkup(keyboard)

                context.bot.send_photo(chat_id=update.effective_chat.id, photo=cover_horizontal_image_url_cleaned, caption=message, reply_markup=reply_markup, parse_mode='html')

            except telegram.error.BadRequest as e:
                print(f"Error sending photo with cover_horizontal_image_url: {e}")
                keyboard = [
                    [

                        telegram.InlineKeyboardButton("Watch Trailer", url=film_info['trailer_url'])
                    ]
                ]
                reply_markup = telegram.InlineKeyboardMarkup(keyboard)

                context.bot.send_photo(chat_id=update.effective_chat.id, photo=still_url, caption=message, reply_markup=reply_markup, parse_mode='html')

dispatcher.add_handler(CommandHandler('recommend', recommend))
dispatcher.add_handler(CallbackQueryHandler(button))


def search_series(series_name):
    try:
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'en',
            'region': 'US',
            'query': series_name,
            'include_adult': 'true'
        }
        response = requests.get('https://api.themoviedb.org/3/search/tv', params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        else:
            return []
    except Exception as e:
        print(f"Error searching for series: {e}")
        raise

def generate_series_link(series_id, series_name):
    formatted_name = series_name.lower().replace(' ', '-')
    return f"https://movie-web.app/media/tmdb-tv-{series_id}-{formatted_name}"

def series(update, context):
    if len(context.args) == 0:
        update.message.reply_text('Please provide a series name after /series.')
        return

    series_name = ' '.join(context.args)

    try:
        series_list = search_series(series_name)

        if not series_list:
            update.message.reply_text('No series found.')
            return

        for series in series_list[:1]:
            if series['poster_path']:
                poster_url = f"https://image.tmdb.org/t/p/original/{series['poster_path']}"
                formatted_title = series['name'].upper()
                release_date = series.get('first_air_date', '')[:4]  # Extracting the year from first air date
                overview = series['overview']
                vote_average = series['vote_average']
                link = generate_series_link(series['id'], series['name'])  # Streaming link generation
                keyboard = [
                    [telegram.InlineKeyboardButton("Stream", url=link)]
                ]
                reply_markup = telegram.InlineKeyboardMarkup(keyboard)

                caption = f"<b>{formatted_title} | {release_date}</b>\n\n{overview}\n\n<b>⭐ Rating: <span class='tg-spoiler'>{vote_average} </span></b>\nPlease reload the browser if it says failed.\nCopyright Legality: \n/copyright@MovicedBot"

                context.bot.send_photo(chat_id=update.effective_chat.id, photo=poster_url, caption=caption, parse_mode='html', reply_markup=reply_markup)

            else:
                message = f"<b>{series['name']}</b>\n"
                message += "\n<b>Poster not found</b>\n"
                update.message.reply_text(message, parse_mode='html')

    except Exception as e:
        print(f"Error searching for series: {e}")
        update.message.reply_text('An error occurred while searching for series.')


dispatcher.add_handler(CommandHandler('series', series))


def search_movies(movie_name):
    try:
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'en',
            'region': 'US',
            'query': movie_name,
            'include_adult': 'true'
        }
        response = requests.get(TMDB_SEARCH_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        else:
            return []
    except Exception as e:
        print(f"Error searching for movies: {e}")
        raise
def generate_movie_link(movie_id, movie_title):
    formatted_title = movie_title.lower().replace(' ', '-')
    return f"https://movie-web.app/media/tmdb-movie-{movie_id}-{formatted_title}"
    pass
def get_video_key(movie_id):
    try:
        tmdb_movie = Movie()
        tmdb_movie.api_key = TMDB_API_KEY  # Set the API key for the Movie() instance
        videos = tmdb_movie.videos(movie_id)
        if videos and videos.get('results'):
            return videos['results'][0].get('key')  # Assuming the first video listed is the trailer
        else:
            return None
    except Exception as e:
        print(f"Error fetching video key: {e}")
        return None
        pass



def searching_movie(movie_name):
    tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
    tmdb_response = requests.get(tmdb_url)
    tmdb_data = tmdb_response.json()

    if tmdb_data['results']:
        movie = tmdb_data['results'][0]

        tmdb_movie_id = movie['id']

        external_ids_url = f"https://api.themoviedb.org/3/movie/{tmdb_movie_id}/external_ids?api_key={TMDB_API_KEY}"
        external_ids_response = requests.get(external_ids_url)
        external_ids_data = external_ids_response.json()

        if 'imdb_id' in external_ids_data:
            imdb_id_from_tmdb_api = external_ids_data['imdb_id']

            year = movie['release_date'][:4]
            tmdb_id = movie['id']
            real_title_from_tmdb_api = movie['title']

            scrape_url = f"https://api.moviewebdotapp-cf14262.workers.dev/scrape?type=movie&releaseYear={year}&imdbId={imdb_id_from_tmdb_api}&tmdbId={tmdb_id}&title={real_title_from_tmdb_api}"

            response = requests.get(scrape_url)

            playlist_match = re.search(r'"playlist":"([^"]+)"', response.text)

            if playlist_match:
                playlist_link = playlist_match.group(1)
                return playlist_link
            else:
                return "No playlist link found in the response."
        else:
            return "IMDb ID not found for the given movie."
    else:
        return "No results found for the given query."



def save_search_history(movie_name):
    try:
        with open('search_history.json', 'r') as f:
            search_history = json.load(f)
    except FileNotFoundError:
        search_history = []

    search_entry = {
        'movie_name': movie_name,
        'date_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    search_history.append(search_entry)

    with open('search_history.json', 'w') as f:
        json.dump(search_history, f, indent=4)
def movie(update, context):



    if len(context.args) == 0:
        update.message.reply_text('Please provide a movie name after /movie.')
        return


    movie_name = ' '.join(context.args)


    try:
        movies = search_movies(movie_name)

        if not movies:
            update.message.reply_text('No movies found.')
            return

        for movie in movies[:1]:
            if movie['poster_path']:
                poster_url = f"https://image.tmdb.org/t/p/original/{movie['poster_path']}"
                formatted_title = movie['title'].upper()
                release_date = movie['release_date'][:4]  # Extracting the year from release date
                overview = movie['overview']
                vote_average = movie['vote_average']
                link = searching_movie(movie_name)  # Replace this with your streaming link generation
                movie_web_link =   generate_movie_link(movie['id'], movie['title'])  # Replace this with your streaming link generation
                video_key = get_video_key(movie['id'])
                if video_key:
                    youtube_link = f"https://youtube.com/watch?v={video_key}"
                    keyboard = [
                        [
                            telegram.InlineKeyboardButton("Stream", url=movie_web_link),
                            telegram.InlineKeyboardButton("Watch Trailer", url=youtube_link)
                        ]
                    ]

                    reply_markup = telegram.InlineKeyboardMarkup(keyboard)
                else:
                    reply_markup = telegram.InlineKeyboardMarkup([[telegram.InlineKeyboardButton("Stream", url=movie_web_link)]])
                caption = f"<b>{formatted_title} | {release_date}</b>\n\n{overview}\n\n<b>⭐ Rating: <span class='tg-spoiler'>{vote_average} </span></b>"
 
                if link and link.startswith('https://'):
                    caption += f"\n\n⚠️ If you face any error in the streaming website here is the Direct Link, open and share it with VLC media app: <a href='{link}'>Direct link share it with vlc</a>\n\nDownload from Playstore: <a href='https://play.google.com/store/apps/details?id=org.videolan.vlc'>Vlc Media Player</a>\n"

                caption += "\nCopyright Legality:\n/copyright@MovicedBot"                
                save_search_history(movie_name)
                
                context.bot.send_photo(chat_id=update.effective_chat.id, photo=poster_url, caption=caption, parse_mode='html', reply_markup=reply_markup)
            else:
                save_search_history(movie_name)

                message = f"<b>{movie['title']}</b>\n"
                message += "\n<b>Poster not found</b>\n"
                update.message.reply_text(message, parse_mode='html')





    except Exception as e:
        print(f"Error searching for movies: {e}")
        update.message.reply_text('An error occurred while searching for movies.')

dispatcher.add_handler(CommandHandler('movie', movie))


def inline_movie(update, context):
    query = update.inline_query.query

    if query:
        try:
            movie_results = tmdb.Search().movie(query=query)['results']

            results = []
            for movie in movie_results[:5]:
                title = movie['title']
                release_date = movie.get('release_date', '')[:4] if 'release_date' in movie else ''
                overview = movie['overview']
                vote_average = movie.get('vote_average', '') if 'vote_average' in movie else ''

                link = generate_movie_link(movie['id'], title)
                genre_names = []
                genre_ids = movie.get("genre_ids", [])
                if genre_ids:
                    genre_url = "https://api.themoviedb.org/3/genre/movie/list"
                    genre_response = requests.get(genre_url, params={"api_key": TMDB_API_KEY})
                    genre_data = genre_response.json()
                    genre_map = {genre["id"]: genre["name"] for genre in genre_data["genres"]}
                    genre_names = [genre_map.get(genre_id) for genre_id in genre_ids]
                try:
                    language_code = movie.get("original_language")
                    language_response = requests.get("https://api.themoviedb.org/3/configuration/languages", params={"api_key": TMDB_API_KEY})
                    language_data = language_response.json()
                    language_details = next((lang for lang in language_data if lang["iso_639_1"] == language_code), None)
                    language_name = language_details["english_name"] if language_details else language_code
                except (KeyError, IndexError):
                    language_name = language_code  # Handle potential errors gracefully


                synopsis = movie.get("overview", "").split(".")[0] + "."  # Extract the first sentence
                caption = f"<b>🎬🍿 {title.upper()} ({release_date})</b>\n\n🎭: {', '.join(genre_names)}\n🗣️: {language_name}\n⭐: {vote_average} by @movicedbot\n\n💬 {synopsis}"

                if movie.get('poster_path'):  # If backdrop not available, use poster
                    backdrop_url = ''
                    if movie.get('backdrop_path'):
                        images_url = f"https://api.themoviedb.org/3/movie/{movie['id']}/images?language=en-US&include_image_language=en"
                        images_response = requests.get(images_url, params={"api_key": TMDB_API_KEY})
                        images_data = images_response.json().get('backdrops', [])
                        if images_data:
                            backdrop_url = f"https://image.tmdb.org/t/p/original/{images_data[0]['file_path']}"

                    photo_url = backdrop_url if backdrop_url else (f"https://image.tmdb.org/t/p/original/{movie['backdrop_path']}" if movie.get('backdrop_path') else f"https://image.tmdb.org/t/p/original/{movie['poster_path']}")

                    poster_urlt = f"https://image.tmdb.org/t/p/original/{movie['poster_path']}"
                    results.append(
                        telegram.InlineQueryResultPhoto(
                            id=movie['id'],
                            title=title,
                            description=overview,
                            thumb_url=poster_urlt,
                            photo_url=photo_url,
                            caption=caption,
                            parse_mode='html',
                            reply_markup=create_inline_keyboard(movie, link)
                        )
                    )
                else:  # If neither backdrop nor poster is available
                    results.append(
                        telegram.InlineQueryResultArticle(
                            id=movie['id'],
                            title=title,
                            description=overview,
                            input_message_content=telegram.InputTextMessageContent(
                                f"<b>{title}</b>\n\n<b>Poster and backdrop not found</b>",
                                parse_mode='html'
                            )
                        )
                    )

            update.inline_query.answer(results, cache_time=1)
        except Exception as e:
            print(f"Error searching for movies: {e}")

def create_inline_keyboard(movie, link):
    buttons = []
    video_key = get_video_key(movie['id'])  # Assuming this function exists

    if video_key:
        buttons.append([telegram.InlineKeyboardButton("Watch Trailer ▶", url=f"https://youtube.com/watch?v={video_key}")])

    return telegram.InlineKeyboardMarkup(buttons)

dispatcher.add_handler(InlineQueryHandler(inline_movie))

def start(update, context):
    user = update.message.from_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    now = datetime.datetime.now()
    current_date_time = now.strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open('users.json', 'r') as f:
            users_data = json.load(f)
    except FileNotFoundError:
        users_data = {}

    if user_id not in users_data:
        users_data[user_id] = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'date_time': current_date_time  # Add date and time
        }

        with open('users.json', 'w') as f:
            json.dump(users_data, f, indent=4)

        print(f"New user details:\nUser ID: {user_id}\nUsername: {username}\nFirst Name: {first_name}\nLast Name: {last_name}\nDate Time: {current_date_time}")

        profile_photo = context.bot.get_user_profile_photos(user_id=user_id).photos
        if profile_photo:
            photo_file = profile_photo[0][0]
            context.bot.send_photo(
                chat_id=6929312249,  # Your chat ID
                photo=photo_file.file_id,
                caption=f"New user started the bot:\n\nName: {first_name} {last_name}\nUsername: @{username}\nID: {user_id}\nDate Time: {current_date_time}"
            )
        else:
            context.bot.send_message(
                chat_id=6929312249,  # Your chat ID
                text=f"New user started the bot:\n\nName: {first_name} {last_name}\nUsername: @{username}\nID: {user_id}\nDate Time: {current_date_time}"
            )

    gif_url = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExOWN3cDhva2I1bDB3c3I4N3hiaWRoYWxkcWMzN2FlbDY5Zmt5MzIzOSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/U7QkkRwqgiTR1LbSd7/giphy.gif"
    context.bot.send_animation(chat_id=update.effective_chat.id, animation=gif_url, caption=command_descriptions['start'], parse_mode='html')

def insights(update, context):
    try:
        with open('users.json', 'r') as f:
            users_data = json.load(f)
        with open('search_history.json', 'r') as f:
            search_history = json.load(f)

        total_users = len(users_data)
        today_date = datetime.datetime.now().date()

        recent_users = [user for user in users_data.values() if datetime.datetime.strptime(user['date_time'], "%Y-%m-%d %H:%M:%S").date() == today_date]
        recent_user_count = len(recent_users)
        total_searches = len(search_history)

        average_searches_per_user = total_searches / max(total_users, 1)  # Avoid division by zero



        daily_user_counts = {}
        today = datetime.date.today()
        for i in range(30):
            date = today - datetime.timedelta(days=i)
            daily_user_counts[date.strftime("%Y-%m-%d")] = sum(1 for user in users_data.values() if user['date_time'].startswith(date.strftime("%Y-%m-%d")))

        plt.figure(figsize=(8, 4), facecolor='#1A24FF')  # Adjust figure size as needed
        plt.bar(daily_user_counts.keys(), daily_user_counts.values(), color='#252323')
        plt.xlabel("Date", color='#FFFFFF')
        plt.ylabel("Number of Users", color='#FFFFFF')
        plt.title("Daily User Growth of MOVICED Bot (Last 30 Days)", color='#FFFFFF')
        plt.xticks(rotation=45, ha='right')  # Rotate x-axis labels for readability
        plt.tight_layout()  # Adjust layout for better spacing
        ax = plt.gca()
        ax.patch.set_facecolor("#1A24FF")
        plt.gca().spines["top"].set_color("#1A24FF")
        plt.gca().spines["right"].set_color("#1A24FF")

        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='PNG')
        img_bytes.seek(0)  # Rewind the buffer
        photo_message = context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_bytes, caption="Generating insights...", reply_to_message_id=update.message.message_id)

        insight_message = f"‎\n<b>🤖 Moviced Bot Insights:</b>\n\n" \
                          f"- Total Users: {total_users}\n" \
                          f"- Users joined today: {recent_user_count}\n" \
                          f"- Total Movie Searches: {total_searches}\n" \
                          f"- Average Movie Searches per User: {average_searches_per_user:.0f}\n‎"
        context.bot.edit_message_caption(chat_id=update.effective_chat.id, message_id=photo_message.message_id, caption=insight_message, parse_mode='html')

    except FileNotFoundError:
        context.bot.send_message(chat_id=update.effective_chat.id, text="No user data found yet.", reply_to_message_id=update.message.message_id)
OWNER_ID = 6929312249
sent_messages = {}  # Store sent messages for editing/deleting

def send_message(update, context):
    args = context.args
    if len(args) >= 2:
        user_id = int(args[0])
        message_text = ' '.join(args[1:])

        if update.effective_user.id == OWNER_ID:
            sent_message = context.bot.send_message(chat_id=user_id, text=message_text)
            sent_messages[sent_message.message_id] = {
                'chat_id': user_id,
                'message_id': sent_message.message_id
            }
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Message sent successfully to user {user_id}. Message ID: {sent_message.message_id}")
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="You are not authorized to send messages.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Invalid format. Use /sendmessage user_id your_message")


def dlt(update, context):
    if update.effective_user.id == OWNER_ID:
        replied_message = update.message.reply_to_message
        if replied_message:
            replied_text = replied_message.text.split('. Message ID: ')
            if len(replied_text) == 2 and replied_text[0].startswith("Message sent successfully to user "):
                user_id = int(replied_text[0].split('user ')[-1])
                message_id = int(replied_text[1])
                context.bot.delete_message(chat_id=user_id, message_id=message_id)
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f"Message with ID {message_id} in chat {user_id} deleted successfully.")
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text="Invalid format. Reply to the success message to delete.")
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Reply to the success message to delete.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="You are not authorized to use this command.")


def edit(update, context):
    if update.effective_user.id == OWNER_ID:
        replied_message = update.message.reply_to_message
        if replied_message:
            replied_text = replied_message.text.split('. Message ID: ')
            if len(replied_text) == 2 and replied_text[0].startswith("Message sent successfully to user "):
                user_id = int(replied_text[0].split('user ')[-1])
                message_id = int(replied_text[1])
                new_text = ' '.join(context.args)
                context.bot.edit_message_text(chat_id=user_id, message_id=message_id, text=new_text)
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f"Message with ID {message_id} in chat {user_id} edited successfully.")
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text="Invalid format. Reply to the success message to edit.")
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Reply to the success message to edit.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="You are not authorized to use this command.")

def help(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=command_descriptions['help'], parse_mode='html')

def copyright(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=command_descriptions['copyright'])

def dmca(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=command_descriptions['DMCA'])

def faq(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=command_descriptions['faq'], parse_mode='html')

def dev(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=command_descriptions['dev'], parse_mode='html')


dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('dlt', dlt))
dispatcher.add_handler(CommandHandler('edit', edit))
dispatcher.add_handler(CommandHandler('insights', insights))
dispatcher.add_handler(CommandHandler('sendmessage', send_message))
dispatcher.add_handler(CommandHandler('help', help))
dispatcher.add_handler(CommandHandler('copyright', copyright))
dispatcher.add_handler(CommandHandler('DMCA', dmca))
dispatcher.add_handler(CommandHandler('faq', faq))
dispatcher.add_handler(CommandHandler('dev', dev))
updater.start_polling()
updater.idle()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def gpt(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! I'm your ChatGPT. How can I help you?")

# Message handler to process user messages
def handle_message(update, context):
    message_text = update.effective_message.text

    response = requests.get(f"https://guruapi.tech/api/chatgpt?text={message_text}")
    if response.status_code == 200:
        bot_response = response.json()["response"]
        context.bot.send_message(chat_id=update.effective_chat.id, text=bot_response)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I couldn't process your request.")

# Create the updater and dispatcher
updater = Updater(BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Add the handlers to the dispatcher
start_handler = CommandHandler('gpt', gpt)
message_handler = MessageHandler(Filters.text & (~Filters.command), handle_message)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(message_handler)

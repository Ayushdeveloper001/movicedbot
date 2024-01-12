import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultPhoto, InputMediaPhoto, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, InlineQueryHandler, Filters
import random
import emoji
from tmdbv3api import Movie
import requests
import json
import datetime
from collections import OrderedDict
import tmdbsimple as tmdb  # For TMDB API interactions
import matplotlib.pyplot as plt
import io
import locale
from urllib.parse import quote
import numpy as np  # Import NumPy for calculations
# Replace with your actual bot token
BOT_TOKEN = ''
# Create a TMDB object with your TMDB API key
# Define command descriptions

command_descriptions = {
    'help': "🎬 Watch your favourite shows and movies with this open source streaming bot.\n\nUse /movie moviename command to Search Movies!\n\nUse /series seriesname command to Search Series! (Do not write Season or Episode number, you should be able to choose it in the external link)\n\n<b>Useful Commands:</b>\n\nhelp - Streaming Bot \ncopyright - Disclaimer Notice \nDMCA - Copyright Reporting \nstart - About Moviced \nfaq - Common Questions \ndev - Source Code",
    'copyright': "Moviced does not host any files, it merely links to 3rd party services. Legal issues should be taken up with the file hosts and providers. Moviced is not responsible for any media files shown by the video providers.",
    'dev': "We believe in transparency. Therefore, we've made our bot open-source so that our users can inspect the source code, understand its functionality, and how it handles their data.\n\nFor developers, here is our <a href='https://drive.google.com/file/d/15JYITtcEssy9Hif2LHbmkiyoDw1aXXAo/view?usp=sharing'>View Source Code</a>\n\nWe do not store or sell users' data in any form. Our policy strictly prohibits such practices.",
    'DMCA': "Welcome to the MovicedBot's DMCA! We respect intellectual property rights and want to address any copyright concerns swiftly. If you believe your copyrighted work has been improperly used on our platform, please send a detailed DMCA notice to the email below. Please include a description of the copyrighted material, your contact details, and a statement of good faith belief. We're committed to resolving these matters promptly and appreciate your cooperation in keeping MovicedBot a place that respects creativity and copyrights.\n\n✉️ religiondotscience@gmail.com",
    'start': "<b>About Moviced</b>\n\nMoviced is a Bot that searches the internet for streams. The team aims for a mostly minimalistic approach to consuming content.\n\nUse /movie moviename command to Search Movies!\n\nUse /series seriesname to Search Series! (Do not write Season or Episode number)\n\nUse /recommend to Find random underrated movies!",
    'faq': "<b>Common questions</b>\n\n<b>1. Where does the content come from?</b>\n\nMovicedBot does not host any content. When you click on something to watch, the internet is searched for the selected media (On the loading screen and in the 'video sources' tab you can see which source you're using). Media never gets uploaded by Moviced, everything is through this searching mechanism.\n\n<b>2. Where can I request a show or movie?</b>\n\nIt's not possible to request a show or movie, Moviced does not manage any content. All content is viewed through sources on the internet.\n\n<b>3. The search results display the show or movie, why can't I play it?</b>\n\nOur search results are powered by The Movie Database (TMDB) and display regardless of whether our sources actually have the content."
}

# Create updater and dispatcher
updater = Updater(BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Replace with your actual TMDB API key
TMDB_API_KEY = ''

tmdb.API_KEY = ''

# URL for TMDB movie search
TMDB_SEARCH_URL = 'https://api.themoviedb.org/3/search/movie?'

# Load data from the JSON file
with open('movies_data.json', 'r') as file:
    movie_data = json.load(file)

# Define the '/random' command
# Define the '/random' command
def random_movie(update, context):
    # Get a random movie from the list
    random_movie_entry = random.choice(movie_data)
    film_info = random_movie_entry.get('film')
    if not film_info:
        update.message.reply_text('Movie information not found in the selected entry.')
        return

    # Extract the cover_artwork_horizontal image URL and remove extra text
    artworks = film_info.get('artworks', [])
    cover_horizontal_image_url = next((artwork['image_url'] for artwork in artworks if artwork['format'] == 'cover_artwork_horizontal'), None)
    still_url = film_info.get('still_url', None)
    # Extract the genres
    genred = film_info.get('genres', [])
    # If cover_artwork_horizontal image URL not found or fails, use the still URL
    if not cover_horizontal_image_url:
        cover_horizontal_image_url = still_url

    # Prepare the message with movie details
    message = f"<b>{film_info['title'].upper()} | {film_info['year']}</b>\n\n"
    message += f"<b>Genres:</b> {', '.join(genred)}\n\n"
    message += f"{film_info['short_synopsis']}\n\n"
    message += f"<b>⭐ Rating: <span class='tg-spoiler'>{film_info['average_rating_out_of_ten']}</span></b>\n\n"
    message += "Copyright Legality:\n/copyright@MoviedBot"

    # Remove the ?numbers part from the URL
    cover_horizontal_image_url_cleaned = cover_horizontal_image_url.split('?')[0]

    try:
        # Send the movie image as a photo using cover_horizontal_image_url
        keyboard = [
            [
                telegram.InlineKeyboardButton("Watch Trailer", url=f"https://elfin-peridot-orbit.glitch.me/source?source={film_info['trailer_url']}"),
                telegram.InlineKeyboardButton("Reload ⟳", callback_data='reload_random')
            ]
        ]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)

        # Send a "Loading..." message before sending the image
        loading_message = context.bot.send_message(chat_id=update.effective_chat.id, text="Loading...")

        # Send the photo
        sent_message = context.bot.send_photo(chat_id=update.effective_chat.id, photo=cover_horizontal_image_url_cleaned, caption=message, reply_markup=reply_markup, parse_mode='html')
        # Delete the "Loading..." message once the photo is sent
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_message.message_id)

        # Store the sent message's ID to be used for deletion
        context.user_data['last_recommendation_message'] = sent_message.message_id

        # Store the film info in user data to use in case of reload
        context.user_data['last_recommendation_film_info'] = film_info

    except telegram.error.BadRequest as e:
        print(f"Error sending photo with cover_horizontal_image_url: {e}")
        send_alternative_image(update, context, message, still_url, film_info)  # Sending alternative image and handling reload
        # Delete the "Loading..." message once the photo is sent
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_message.message_id)

def send_alternative_image(update, context, message, image_url, film_info):
    try:
        # Sending using alternative image URL
        keyboard = [
            [
                telegram.InlineKeyboardButton("Watch Trailer", url=f"https://elfin-peridot-orbit.glitch.me/source?source={film_info['trailer_url']}"),
                telegram.InlineKeyboardButton("Reload ⟳", callback_data='reload_random')
            ]
        ]
        reply_markup = telegram.InlineKeyboardMarkup(keyboard)

        # Send the photo
        sent_message = context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url, caption=message, reply_markup=reply_markup, parse_mode='html')


        # Store the sent message's ID and film info to be used for deletion and reload
        context.user_data['last_recommendation_message'] = sent_message.message_id
        context.user_data['last_recommendation_film_info'] = film_info

    except telegram.error.BadRequest as e:
        print(f"Error sending photo with image_url: {e}")
        update.message.reply_text("Failed to load the image.")



# Handle the reload button callback
# Handle the reload button callback
def reload_random_movie(update, context):
    query = update.callback_query
    query.answer()

    # Delete the last recommendation message
    last_message_id = context.user_data.get('last_recommendation_message')
    if last_message_id:
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=last_message_id)

    # Provide a new random movie recommendation
    if 'last_recommendation_film_info' in context.user_data:
        # Use the stored film info for the new recommendation
        context.user_data.pop('last_recommendation_film_info')
        random_movie(update, context)
    else:
        # If film info not found, provide a new random recommendation as before
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

# Function to display genres
# Function to display genres
def genres(update, context):
    genres = [
        'Romance', 'Comedy', 'Animation', 'Crime', 'Drama', 'Sci-Fi', 'War', 'Western', 'Adventure',
        'Silent', 'Short', 'Horror', 'History', 'Biography', 'Film noir', 'Action',
        'Cult', 'Thriller', 'Fantasy', 'Documentary', 'Avant-Garde', 'Mystery'
    ]

    # Split genres into chunks of three for rows
    keyboard = [genres[i:i + 3] for i in range(0, len(genres), 3)]
    keyboard = [[InlineKeyboardButton(genre, callback_data=f'genre_{genre}') for genre in row] for row in keyboard]

    reply_markup = InlineKeyboardMarkup(keyboard)
    # Check if there's an existing message to edit
    if context.user_data.get('genre_message_id'):
        messaged = update.callback_query.edit_message_text('Choose a genre:', reply_markup=reply_markup)
        context.user_data['genre_list_message_id'] = messaged.message_id
    else:
        # Send a new message if there's no text to edit
        message = context.bot.send_message(chat_id=update.effective_chat.id, text='Choose a genre:', reply_markup=reply_markup)
        # Save the message ID for later reference
        context.user_data['genre_message_id'] = message.message_id

# Function to handle button actions
def button(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'random':
        random_movie(update, context)
    elif query.data == 'genres':
        genres(update, context)
    elif query.data == 'back':
        # Check if there's an existing message to edit and display genres
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

            # Extract the cover_artwork_horizontal image URL and remove extra text
            artworks = film_info.get('artworks', [])
            cover_horizontal_image_url = next((artwork['image_url'] for artwork in artworks if artwork['format'] == 'cover_artwork_horizontal'), None)
            still_url = film_info.get('still_url', None)
            # Extract the genres
            genred = film_info.get('genres', [])
            # If cover_artwork_horizontal image URL not found or fails, use the still URL
            if not cover_horizontal_image_url:
                cover_horizontal_image_url = still_url

            # Prepare the message with movie details
            message = f"<b>{film_info['title'].upper()} | {film_info['year']}</b>\n\n"
            message += f"<b>Genres:</b> {', '.join(genred)}\n\n"
            message += f"{film_info['short_synopsis']}\n\n"
            message += f"<b>⭐ Rating: <span class='tg-spoiler'>{film_info['average_rating_out_of_ten']}</span></b>\n\n"
            message += "Copyright Legality:\n/copyright@MovicedBot"

            # Remove the ?numbers part from the URL
            cover_horizontal_image_url_cleaned = cover_horizontal_image_url.split('?')[0]
            if not cover_horizontal_image_url_cleaned:
                cover_horizontal_image_url_cleaned = still_url
            try:
                # Send the movie image as a photo using cover_horizontal_image_url
                keyboard = [
                    [

                        telegram.InlineKeyboardButton("Watch Trailer", url=film_info['trailer_url'])
                    ]
                ]

                reply_markup = telegram.InlineKeyboardMarkup(keyboard)

                # Update the existing message with the movie details
                context.bot.send_photo(chat_id=update.effective_chat.id, photo=cover_horizontal_image_url_cleaned, caption=message, reply_markup=reply_markup, parse_mode='html')

            except telegram.error.BadRequest as e:
                print(f"Error sending photo with cover_horizontal_image_url: {e}")
                # Always include the "Watch Trailer" button, regardless of image loading issues
                keyboard = [
                    [

                        telegram.InlineKeyboardButton("Watch Trailer", url=film_info['trailer_url'])
                    ]
                ]
                reply_markup = telegram.InlineKeyboardMarkup(keyboard)

                # Update the existing message with the movie details
                context.bot.send_photo(chat_id=update.effective_chat.id, photo=still_url, caption=message, reply_markup=reply_markup, parse_mode='html')

# Command handler for /recommend
dispatcher.add_handler(CommandHandler('recommend', recommend))
# Callback handler for button presses
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
                # Creating the Stream button for the streaming link
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

# ... (Previous code remains unchanged)

# Add command handlers to dispatcher including the new 'series' command
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
def save_search_history(movie_name):
    try:
        # Read existing searches from JSON file, if it exists
        with open('search_history.json', 'r') as f:
            search_history = json.load(f)
    except FileNotFoundError:
        search_history = []

    # Append search entry to existing or newly created search history
    search_entry = {
        'movie_name': movie_name,
        'date_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    search_history.append(search_entry)

    # Save the updated searches back to the JSON file
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
                link = generate_movie_link(movie['id'], movie['title'])  # Replace this with your streaming link generation
                # Generating the YouTube link for the trailer if available
                video_key = get_video_key(movie['id'])
                if video_key:
                    youtube_link = f"https://youtube.com/watch?v={video_key}"
                    # Creating the Watch Trailer button
                    keyboard = [
                        [
                            telegram.InlineKeyboardButton("Stream", url=link),
                            telegram.InlineKeyboardButton("Watch Trailer", url=youtube_link)
                        ]
                    ]

                    reply_markup = telegram.InlineKeyboardMarkup(keyboard)
                else:
                    # If no trailer available, display only the Stream button
                    reply_markup = telegram.InlineKeyboardMarkup([[telegram.InlineKeyboardButton("Stream", url=link)]])

                caption = f"<b>{formatted_title} | {release_date}</b>\n\n{overview}\n\n<b>⭐ Rating: <span class='tg-spoiler'>{vote_average} </span></b>\nPlease reload the browser if it says failed.\nCopyright Legality: \n/copyright@MovicedBot"
                # Save the search history to the JSON file
                save_search_history(movie_name)

                # Sending the photo with appropriate buttons
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
                # Handle cases where vote average is not available
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
                    # Fetch backdrop images
                    backdrop_url = ''
                    if movie.get('backdrop_path'):
                        images_url = f"https://api.themoviedb.org/3/movie/{movie['id']}/images?language=en-US&include_image_language=en"
                        images_response = requests.get(images_url, params={"api_key": TMDB_API_KEY})
                        images_data = images_response.json().get('backdrops', [])
                        if images_data:
                            # Get the first backdrop directly
                            backdrop_url = f"https://image.tmdb.org/t/p/original/{images_data[0]['file_path']}"

                    # Set photo_url to backdrop_url if available, else to poster_url
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
            # Handle the error case

def create_inline_keyboard(movie, link):
    buttons = []
    video_key = get_video_key(movie['id'])  # Assuming this function exists

    if video_key:
        buttons.append([telegram.InlineKeyboardButton("Watch Trailer ▶", url=f"https://youtube.com/watch?v={video_key}")])

    return telegram.InlineKeyboardMarkup(buttons)
# ... (Rest of your bot code, including CommandHandler for /start)

dispatcher.add_handler(InlineQueryHandler(inline_movie))

# Define command handlers
def start(update, context):
    user = update.message.from_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    # Get current date and time
    now = datetime.datetime.now()
    current_date_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # Load existing user data from JSON file (if it exists)
    try:
        with open('users.json', 'r') as f:
            users_data = json.load(f)
    except FileNotFoundError:
        users_data = {}

    # Only add or update if the user ID doesn't already exist
    if user_id not in users_data:
        users_data[user_id] = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'date_time': current_date_time  # Add date and time
        }

        # Save updated user data to JSON file
        with open('users.json', 'w') as f:
            json.dump(users_data, f, indent=4)

        # Print user details to console
        print(f"New user details:\nUser ID: {user_id}\nUsername: {username}\nFirst Name: {first_name}\nLast Name: {last_name}\nDate Time: {current_date_time}")

        # Get user's profile photo
        profile_photo = context.bot.get_user_profile_photos(user_id=user_id).photos
        if profile_photo:
            # Get the largest available photo (last in the list)
            photo_file = profile_photo[0][0]
            # Send the user's profile photo and text as caption
            context.bot.send_photo(
                chat_id=6929312249,  # Your chat ID
                photo=photo_file.file_id,
                caption=f"New user started the bot:\n\nName: {first_name} {last_name}\nUsername: @{username}\nID: {user_id}\nDate Time: {current_date_time}"
            )
        else:
            # If no profile photo is available, send only text
            context.bot.send_message(
                chat_id=6929312249,  # Your chat ID
                text=f"New user started the bot:\n\nName: {first_name} {last_name}\nUsername: @{username}\nID: {user_id}\nDate Time: {current_date_time}"
            )

    # Your existing code to send the GIF and command description
    gif_url = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExOWN3cDhva2I1bDB3c3I4N3hiaWRoYWxkcWMzN2FlbDY5Zmt5MzIzOSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/U7QkkRwqgiTR1LbSd7/giphy.gif"
    context.bot.send_animation(chat_id=update.effective_chat.id, animation=gif_url, caption=command_descriptions['start'], parse_mode='html')

# Define the /insight command handler
def insights(update, context):
    try:
        # Load user data from both files
        with open('users.json', 'r') as f:
            users_data = json.load(f)
        # Read existing user searches from JSON file
        with open('search_history.json', 'r') as f:
            search_history = json.load(f)

        # Calculate insights from both sources
        total_users = len(users_data)
        # Get today's date
        today_date = datetime.datetime.now().date()

        # Filter users who joined today
        recent_users = [user for user in users_data.values() if datetime.datetime.strptime(user['date_time'], "%Y-%m-%d %H:%M:%S").date() == today_date]
        recent_user_count = len(recent_users)
        # Calculate total searches
        total_searches = len(search_history)

        average_searches_per_user = total_searches / max(total_users, 1)  # Avoid division by zero



        # Calculate daily user counts for the last 30 days
        daily_user_counts = {}
        today = datetime.date.today()
        for i in range(30):
            date = today - datetime.timedelta(days=i)
            daily_user_counts[date.strftime("%Y-%m-%d")] = sum(1 for user in users_data.values() if user['date_time'].startswith(date.strftime("%Y-%m-%d")))

        # Create the bar graph
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

        # Convert the graph to an image and send it
        img_bytes = io.BytesIO()
        plt.savefig(img_bytes, format='PNG')
        img_bytes.seek(0)  # Rewind the buffer
        photo_message = context.bot.send_photo(chat_id=update.effective_chat.id, photo=img_bytes, caption="Generating insights...", reply_to_message_id=update.message.message_id)

        # Edit the caption with the insights text
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

        # Check if the sender is the owner
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

# Add the message handlers

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
# Start the bot
updater.start_polling()
updater.idle()

import streamlit as st
import numpy as np 
import pandas as pd 
import webbrowser
import random
import json
import time
from bokeh.models.widgets import Div
import pygsheets
import tempfile
import json
import requests

def _google_creds_as_file():
    temp = tempfile.NamedTemporaryFile()
    temp.write(json.dumps({
        "type": st.secrets['type'],
        "project_id": st.secrets['project_id'],
        "private_key_id": st.secrets['private_key_id'],
        "private_key": st.secrets['private_key'],
        "client_email":st.secrets['client_email'] ,
        "client_id": st.secrets['client_id'],
        "auth_uri": st.secrets['auth_uri'],
        "token_uri": st.secrets['token_uri'],
        "auth_provider_x509_cert_url": st.secrets['auth_provider_x509_cert_url'],
        "client_x509_cert_url": st.secrets['client_x509_cert_url']
    }).encode('utf-8'))
    temp.flush()
    return temp

creds_file = _google_creds_as_file()
gc = pygsheets.authorize(service_account_file=creds_file.name)

def generate_random_code():
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789'
    return ''.join(random.choice(letters) for i in range(10))

def display_thank_you(code):
    st.header("Thanks for contributing to this study.")
    st.write('Please submit the following code to MTurk:')
    st.title(code)

def save_data(state):
    last_decisions = np.array(state.last_decisions)
    last_decisions = last_decisions.reshape(last_decisions.shape[0],1)
    data = np.append(state.shown_instances, last_decisions, axis=1)
    df = pd.DataFrame(data)
    df['link_clicked'] = [i in state.link_clicked for i in range(len(last_decisions))]
    df['timestamps'] = state.timestamps
    df['user'] = state.user_code
    df['ratings'] = state.last_decisions
    df['film_info'] = state.film_info[:-1]
    
    sh = gc.open('Study_results_recsys')

    sheetname = f"{state.genre_selected}_{state.user_code}_{state.selected}_{st.session_state.rew_idx}"
    sheet = sh.add_worksheet(sheetname)

    sheet.set_dataframe(df,(0,0))

def init_states():
    user_code = generate_random_code()
    if 'state' not in st.session_state:
        st.session_state['state'] = 'select_genre'
    if 'link_clicked' not in st.session_state:
        st.session_state['link_clicked'] = []
    if 'user_code' not in st.session_state:
        st.session_state['user_code'] = user_code
    if 'selected' not in st.session_state:
        st.session_state['selected'] = []
    if 'action_idx' not in st.session_state:
        st.session_state['action_idx'] = 0
    if 'progress' not in st.session_state:
        st.session_state['progress'] = 0
    if 'last_decisions' not in st.session_state:
        st.session_state['last_decisions'] = []
    if 'shown_instances' not in st.session_state:
        st.session_state['shown_instances'] = []
    if 'shown_instances' not in st.session_state:
        st.session_state['shown_instances'] = []
    if 'timestamps' not in st.session_state:
        st.session_state['timestamps'] = []
    if 'genre_selected' not in st.session_state:
        st.session_state['genre_selected'] = ""

def set_explanations():
    st.header('Instructions')
    explanation_placeholder = st.empty()
    explanation_placeholder.write(f'Please browse through movies until you find a movie you would like to watch today. Please check out the link at "View the Trailer and get more information." to get more information about the movie and/or watch the trailer. For each movie you check out, please rate it from 1-10 stars, depending on how appealing it is for you to watch.(1: I do not want to watch it - 10: I would love to watch it). Note that you have to review at least 5 movies.')
    explanation_placeholder_3 = st.empty()
    s = '**When you found a movie you like to watch today, please click Next to record your rating and then click Done.** You will then be able to select your choice from all previous options reviewed. Note that you can choose any of the movies you reviewed before.'
    explanation_placeholder_3.markdown(s)

def empty_widgets(widgets):
    for widget in widgets:
        widget.empty()

def get_film_info(instances):
    omdbapi = st.secrets['omdbapikey']
    curr_idx = st.session_state.selected_sequence[st.session_state['action_idx']]
    id = instances.imdbId.loc[curr_idx]
    if (isinstance(id, pd.Series)):
        id = id.iloc[0]
    id_formatted = ("tt"+str(id))
    id_formatted = id_formatted.replace("tt0", 'tt') if len(str(id)) != 7 else id_formatted
    query = {'i': id_formatted, 'plot':'full'}
    response = requests.get(f'http://www.omdbapi.com/?apikey={omdbapi}&', params=query)
    film_info = response.json()
    return film_info

@st.cache
def read_movies():
    f = open('all.json')
    data = json.load(f)
    movies = pd.read_csv('./data.csv').drop(columns=["Unnamed: 0"]).drop_duplicates(subset="imdbId")
    movies.index = movies.movieId
    idx = 5#random.randint(0,10)
    movies['link'] = movies['link'].apply(lambda x: x.replace('tt0', "tt").replace('tt00', "tt") if len(str(x.split("tt")[-1])) != 8 else x)
    return movies, data, idx

def main():   
    st.set_page_config(layout="wide")
    init_states()   
    set_explanations()   
    movies, sequences, idx = read_movies()
    st.session_state.rew_idx = idx
    unique_genres = list(np.unique(np.array([item for sublist in movies["genrelist"].apply(lambda x: eval(x)) for item in sublist])))
    if st.session_state.state == "select_genre":
        head = st.empty()
        head.header('Select Genre')
        genre = st.empty()
        g_sel = genre.selectbox('Please select a movie genre you like from the following:', unique_genres)
        next_b = st.empty()
        selected_sequence = sequences[g_sel][idx]
        st.session_state.genre_selected = g_sel
        st.session_state.selected_sequence = selected_sequence
        instances = movies.loc[selected_sequence].drop_duplicates(subset="imdbId")
        if next_b.button("Proceed"):
            empty_widgets([genre, next_b, head])
            st.session_state.state = "review_items"
            curr_idx = st.session_state.selected_sequence[st.session_state['action_idx']]
            st.session_state['link'] = instances.link.loc[curr_idx]
            instances = movies.loc[st.session_state.selected_sequence].drop_duplicates(subset="imdbId")

            if 'film_info' not in st.session_state:
                st.session_state['film_info'] = [get_film_info(instances=instances)]
    if st.session_state.state == 'review_items':
        instances = movies.loc[st.session_state.selected_sequence].drop_duplicates(subset="imdbId")
        curr_idx = st.session_state.selected_sequence[st.session_state['action_idx']]
        rev = st.empty()
        rev.header('Review & Rate Movie')
        tit = st.empty()
        tit.title(f'{instances["title"].loc[curr_idx]}')
        st.session_state['link'] = instances.link.loc[curr_idx]
    
        col0, col4 = st.columns([0.2,1]) 
        with col0: 
            image = st.empty()
            image.image(st.session_state['film_info'][st.session_state['action_idx']]['Poster'],width=240)
        with col4:
            plot = st.empty()
            Director = st.empty()
            Writer = st.empty()
            Actors = st.empty()
            Runtime = st.empty()
            plot.markdown(f"**Plot:** {st.session_state['film_info'][st.session_state['action_idx']]['Plot']}")
            Director.markdown(f"**Director:** {st.session_state['film_info'][st.session_state['action_idx']]['Director']}")
            Writer.markdown(f"**Writer:** {st.session_state['film_info'][st.session_state['action_idx']]['Writer']}")
            Actors.markdown(f"**Actors:** {st.session_state['film_info'][st.session_state['action_idx']]['Actors']}")
            Runtime.markdown(f"**Runtime:** {st.session_state['film_info'][st.session_state['action_idx']]['Runtime']}")
            bp = st.empty()
            mk = st.empty()
            if bp.button(f"View the Trailer and get more information."):
                stri = f"Please Click: {st.session_state['link']}"
                mk.markdown(stri)
    
                st.session_state.link_clicked.append(st.session_state['action_idx'])
        slid = st.empty()
        slider_val = slid.slider('Choose a rating from 1 to 10',1,10) 
        col1, col2, col3= st.columns([2,0.8,2]) 
        with col1: 
            st.empty()
        with col2: 
            md = st.empty()
            if slider_val==1: md.markdown(":star:") 
            if slider_val==2: md.markdown(":star::star:") 
            if slider_val==3: md.markdown(":star::star::star:") 
            if slider_val==4: md.markdown(":star::star::star::star:") 
            if slider_val==5: md.markdown(":star::star::star::star::star:") 
            if slider_val==6: md.markdown(":star::star::star::star::star::star:") 
            if slider_val==7: md.markdown(":star::star::star::star::star::star::star:") 
            if slider_val==8: md.markdown(":star::star::star::star::star::star::star::star:") 
            if slider_val==9: md.markdown(":star::star::star::star::star::star::star::star::star:") 
            if slider_val==10: md.markdown(":star::star::star::star::star::star::star::star::star::star:") 
        with col3: 
            st.empty()
        button_placeholder_1 = st.empty()
        if button_placeholder_1.button("Next"):
            instances = movies.loc[st.session_state.selected_sequence].drop_duplicates(subset="imdbId")
            st.session_state.last_decisions.append(slider_val)
            st.session_state.shown_instances.append(instances.loc[curr_idx])
            st.session_state.timestamps.append(time.time())

            st.session_state['action_idx'] += + 1
            curr_idx = st.session_state.selected_sequence[st.session_state['action_idx']]
            st.session_state['link'] = instances.link.loc[curr_idx]
            st.session_state['film_info'].append(get_film_info(instances=instances))
            
            tit.title(f'{instances["title"].loc[curr_idx]}')
            plot.markdown(f"**Plot:** {st.session_state['film_info'][st.session_state['action_idx']]['Plot']}")
            Director.markdown(f"**Director:** {st.session_state['film_info'][st.session_state['action_idx']]['Director']}")
            Writer.markdown(f"**Writer:** {st.session_state['film_info'][st.session_state['action_idx']]['Writer']}")
            Actors.markdown(f"**Actors:** {st.session_state['film_info'][st.session_state['action_idx']]['Actors']}")
            Runtime.markdown(f"**Runtime:** {st.session_state['film_info'][st.session_state['action_idx']]['Runtime']}")
            image.image(st.session_state['film_info'][st.session_state['action_idx']]['Poster'],width=240)

            
        if st.session_state['action_idx'] > 5:
            button_placeholder_2 = st.empty()
            if len(instances) - 1 == st.session_state['action_idx'] or button_placeholder_2.button("Done"):
            
                st.session_state.state = 'select'
                empty_widgets([slid, rev, bp, tit, md, button_placeholder_2, button_placeholder_1, mk])
                empty_widgets([plot, Director, Actors, Writer, Runtime, image])

    if st.session_state.state == 'select':
        h = st.empty()
        h.header("Select Movie")
        if len(st.session_state.shown_instances) == 0:
            st.write("You have to review movies before you can make your decision. Please refresh the page to start again.")
        else:
            data = pd.DataFrame(st.session_state.shown_instances)[['title', 'link']]
        
            sel = st.empty()
            selected_indices = sel.selectbox('Select Movie you would like to watch today:', data.title)

            mid = movies[movies['title'] == selected_indices].movieId.iloc[0]
            st.session_state['selected'] = mid

            tab = st.empty()
            tab.table(data=data.reset_index(drop=True))
            neb = st.empty()
            if neb.button("Finish"):
                st.session_state.state = 'finish'
                empty_widgets([tab, sel])

    if st.session_state.state == 'finish':
            empty_widgets([neb, h])
            save_data(st.session_state)
            display_thank_you(st.session_state['user_code'])

if __name__ == "__main__":
    main()
import streamlit as st
import numpy as np 
import pandas as pd 
import webbrowser
import random
import re, requests
import os, sys
import time


def generate_random_code():
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789'
    return ''.join(random.choice(letters) for i in range(10))

def display_thank_you(code):
    st.header("Thanks for contributing to this study.")
    st.write('Please submit the following code to MTurk:')
    st.title(code)
def download_url(url):
    opener = urllib.request.FancyURLopener({})
    f = opener.open(url)
    content = f.read()
    return content 

def savePage(url, pagepath='page'):
    def savenRename(soup, pagefolder, session, url, tag, inner):
        if not os.path.exists(pagefolder): # create only once
            os.mkdir(pagefolder)
        for res in soup.findAll(tag):   # images, css, etc..
            if res.has_attr(inner): # check inner tag (file object) MUST exists  
                try:
                    filename, ext = os.path.splitext(os.path.basename(res[inner])) # get name and extension
                    filename = re.sub('\W+', '', filename) + ext # clean special chars from name
                    fileurl = urljoin(url, res.get(inner))
                    filepath = os.path.join(pagefolder, filename)
                    # rename html ref so can move html and folder of files anywhere
                    res[inner] = os.path.join(os.path.basename(pagefolder), filename)
                    if not os.path.isfile(filepath): # was not downloaded
                        with open(filepath, 'wb') as file:
                            filebin = session.get(fileurl)
                            file.write(filebin.content)
                except Exception as exc:
                    print(exc, file=sys.stderr)
    session = requests.Session()
    #... whatever other requests config you need here
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    path, _ = os.path.splitext(pagepath)
    pagefolder = path+'_files' # page contents folder
    tags_inner = {'img': 'src', 'link': 'href', 'script': 'src'} # tag&inner tags to grab
    for tag, inner in tags_inner.items(): # saves resource files and rename refs
        savenRename(soup, pagefolder, session, url, tag, inner)
    with open(path+'.html', 'wb') as file: # saves modified html doc
        file.write(soup.prettify('utf-8'))
    return soup.prettify('utf-8')

def save_data(state):
    last_decisions = np.array(state.last_decisions)
    last_decisions = last_decisions.reshape(last_decisions.shape[0],1)
    data = np.append(state.shown_instances, last_decisions, axis=1)
    df = pd.DataFrame(data)
    df['link_clicked'] = [i in state.link_clicked for i in range(len(last_decisions))]
    df['timestamps'] = state.timestamps
    df['ratings'] = [i in state.last_decisions for i in range(len(last_decisions))]
    df.to_csv(f'./review_session_data_{state.genre_selected}_{state.user_code}.csv')

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

@st.cache
def prepare_data(movies, genre):
    filter = movies.genrelist.apply(lambda x: genre in x)
    filtered_movies_genre = movies[filter]
    filtered_movies_not_genre = movies[filter == 0]
    genre_sample = filtered_movies_genre[0:15]
    not_genre_sample = filtered_movies_not_genre[0:35]
    df = pd.concat((genre_sample, not_genre_sample), axis=0)
    instances = df
    return instances

def set_explanations():
    st.header('Instructions')
    explanation_placeholder = st.empty()
    explanation_placeholder.write(f'Please browse through movies until you find a movie you would like to watch today. Please check out the link at "View the Trailer and get more information." to get more information about the movie and/or watch the trailer.For each movie you see, please rate it from 1-5 stars, depending on how appealing it is for you to watch.(1: I\'m probably not going to watch it - 5: I would love to watch it)')
    explanation_placeholder_3 = st.empty()
    s = 'When you found a movie you like to watch today, please click Done. You will then be able to select your choice from all previous options reviewed. Note that you can choose any of the movies you reviewed before.'
    explanation_placeholder_3.write(s)

def empty_widgets(widgets):
    for widget in widgets:
        widget.empty()
@st.cache
def read_movies():
    movies = pd.read_csv('./data.csv')[0:250].drop(columns=["Unnamed: 0"]).sample(frac=1).reset_index(drop=True)
    return movies 
def main():   
    st.set_page_config(layout="wide")
    init_states()   
    set_explanations()   
    movies = read_movies()
    unique_genres = list(np.unique(np.array([item for sublist in movies["genrelist"].apply(lambda x: eval(x)) for item in sublist])))
    if st.session_state.state == "select_genre":
        head = st.empty()
        head.header('Select Genre')
        genre = st.empty()
        g_sel = genre.selectbox('Please select a movie genre you like from the following:', unique_genres)
        next_b = st.empty()
        st.session_state.genre_selected = g_sel
        if next_b.button("Proceed"):
            empty_widgets([genre, next_b, head])
            st.session_state.state = "review_items"
    if st.session_state.state == 'review_items':
        instances = prepare_data(movies, st.session_state.genre_selected)    
        curr_idx = st.session_state['action_idx']
        rev = st.empty()
        rev.header('Review & Rate Movie')
        tit = st.empty()
        tit.title(f'{instances["title"].loc[curr_idx]}')
        bp = st.empty()
        st.session_state['link'] = instances.link.loc[curr_idx]
        if bp.button('View the Trailer and get more information.'):
            webbrowser.open_new_tab(st.session_state['link'])
            st.session_state.link_clicked.append(curr_idx)
        #content = download_url(st.session_state['link'])
        #st.components.v1.html(content, width=None, height=400, scrolling=True)
        slid = st.empty()
        slider_val = slid.slider('Choose a rating from 1 to 5',1,5) 
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
        with col3: 
            st.empty()
        button_placeholder_1 = st.empty()
        if button_placeholder_1.button("Next"):
            st.session_state.last_decisions.append(slider_val)
            st.session_state.shown_instances.append(instances.loc[curr_idx])
            st.session_state.timestamps.append(time.time())
            st.session_state['action_idx'] += + 1
            curr_idx = st.session_state['action_idx']
            st.session_state['link'] = instances.link.loc[curr_idx]
            tit.title(f'{instances["title"].loc[curr_idx]}')
            

        button_placeholder_2 = st.empty()
        if len(instances) - 1 == st.session_state['action_idx'] or button_placeholder_2.button("Done"):
            st.session_state.state = 'select'
            empty_widgets([slid, rev, bp, tit, md, button_placeholder_2, button_placeholder_1])
    if st.session_state.state == 'select':
        h = st.empty()
        h.header("Select Movie")
        data = pd.DataFrame(st.session_state.shown_instances)[['title', 'link']]
        sel = st.empty()
        selected_indices = sel.selectbox('Select Movie you would like to watch today:', data.title)
        st.session_state['selected'] = selected_indices
        tab = st.empty()
        tab.table(data=data)
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
#import module
import streamlit as st
import pandas as pd
import re
import nltk
nltk.download('punkt')
from nltk.tokenize import word_tokenize
from mlxtend.preprocessing import TransactionEncoder
te = TransactionEncoder()
from mlxtend.frequent_patterns import fpgrowth
from mlxtend.frequent_patterns import association_rules
from streamlit_agraph import agraph, Node, Edge, Config
import nltk
nltk.download('wordnet')
from nltk.stem import WordNetLemmatizer
nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
import sys

#===config===
st.set_page_config(
     page_title="Coconut",
     page_icon="🥥",
     layout="wide"
)
st.header("Biderected Keywords Network")
st.subheader('Put your CSV file here ...')

def reset_all():
     st.cache_data.clear()
     st.cache_resource.clear()

def reset_resource():
     st.cache_resource.clear()

@st.cache_data(ttl=3600)
def upload(file):
    uploaded_file = file
    papers = pd.read_csv(uploaded_file)
    return papers

@st.cache_data(ttl=3600)
def conv_txt(file):
    col_dict = {'TI': 'title',
            'SO': 'source title',
            'DT': 'document type',
            'DE': 'author keywords',
            'ID': 'keywords plus',
            'AB': 'abstract',
            'TC': 'cited by',
            'PY': 'year',}
    papers = pd.read_csv(file, sep='\t', lineterminator='\r')
    papers.rename(columns=col_dict, inplace=True)
    return papers

@st.cache_data(ttl=3600)
def get_ext(file):
    extype = file.name
    return extype

#===Read data===
uploaded_file = st.file_uploader("Choose a file", type=['csv', 'txt'], on_change=reset_all)

if uploaded_file is not None:
    extype = get_ext(uploaded_file)
    if extype.endswith('.csv'):
         papers = upload(uploaded_file) 
         st.write(papers)
    elif extype.endswith('.txt'):
         papers = conv_txt(uploaded_file)
         st.write(papers)
    
    @st.cache_data(ttl=3600)
    def get_data_arul():
        list_of_column_key = list(papers.columns)
        list_of_column_key = [k for k in list_of_column_key if 'Keyword' in k]
        return papers, list_of_column_key
     
    papers, list_of_column_key = get_data_arul()

    col1, col2 = st.columns(2)
    with col1:
        method = st.selectbox(
             'Choose method',
           ('Stemming', 'Lemmatization'), on_change=reset_all)
    with col2:
        keyword = st.selectbox(
            'Choose column',
           (list_of_column_key), on_change=reset_all)


    #===body=== 
    @st.cache_data(ttl=3600)
    def clean_arul():
        global keyword, papers
        try:
            arul = papers.dropna(subset=[keyword])
        except KeyError:
            st.error('Error: Please check your Author/Index Keywords column.')
            sys.exit(1)
        arul[keyword] = arul[keyword].map(lambda x: re.sub('-—–', ' ', x))
        arul[keyword] = arul[keyword].map(lambda x: re.sub('; ', ' ; ', x))
        arul[keyword] = arul[keyword].map(lambda x: x.lower())
        arul[keyword] = arul[keyword].dropna()
        return arul

    arul = clean_arul()   

    #===stem/lem===
    @st.cache_data(ttl=3600)
    def lemma_arul():
        lemmatizer = WordNetLemmatizer()
        def lemmatize_words(text):
             words = text.split()
             words = [lemmatizer.lemmatize(word) for word in words]
             return ' '.join(words)
        arul[keyword] = arul[keyword].apply(lemmatize_words)
        return arul
    
    @st.cache_data(ttl=3600)
    def stem_arul():
        stemmer = SnowballStemmer("english")
        def stem_words(text):
            words = text.split()
            words = [stemmer.stem(word) for word in words]
            return ' '.join(words)
        arul[keyword] = arul[keyword].apply(stem_words)
        return arul

    if method is 'Lemmatization':
        arul = lemma_arul()
    else:
        arul = stem_arul()
    
    @st.cache_data(ttl=3600)
    def arm():
        arule = arul[keyword].str.split(' ; ')
        arule_list = arule.values.tolist()  
        te_ary = te.fit(arule_list).transform(arule_list)
        df = pd.DataFrame(te_ary, columns=te.columns_)
        return df
    df = arm()

    col1, col2, col3 = st.columns(3)
    with col1:
        supp = st.slider(
            'Select value of Support',
            0.001, 1.000, (0.010), on_change=reset_resource)
    with col2:
        conf = st.slider(
            'Select value of Confidence',
            0.001, 1.000, (0.050), on_change=reset_resource)
    with col3:
        maxlen = st.slider(
            'Maximum length of the itemsets generated',
            2, 8, (2), on_change=reset_resource)

    tab1, tab2 = st.tabs(["📈 Result & Generate visualization", "📓 Recommended Reading"])
    
    with tab1:
        #===Association rules===
        @st.cache_resource(ttl=3600)
        def freqitem():
            global supp, maxlen
            freq_item = fpgrowth(df, min_support=supp, use_colnames=True, max_len=maxlen)
            return freq_item
        
        @st.cache_resource(ttl=3600)
        def arm_table():
            global conf, freq_item
            res = association_rules(freq_item, metric='confidence', min_threshold=conf) 
            res = res[['antecedents', 'consequents', 'antecedent support', 'consequent support', 'support', 'confidence', 'lift', 'conviction']]
            res['antecedents'] = res['antecedents'].apply(lambda x: ', '.join(list(x))).astype('unicode')
            res['consequents'] = res['consequents'].apply(lambda x: ', '.join(list(x))).astype('unicode')
            return res

        freq_item = freqitem()
        st.write('🚨 The more data you have, the longer you will have to wait.')

        if freq_item.empty:
            st.error('Please lower your value.', icon="🚨")
        else:
            res = arm_table()
            st.dataframe(res, use_container_width=True)
                   
             #===visualize===
                
            if st.button('📈 Generate network visualization'):
                with st.spinner('Visualizing, please wait ....'): 
                     @st.cache_resource(ttl=3600)
                     def map_node():
                        res['to'] = res['antecedents'] + ' → ' + res['consequents'] + '\n Support = ' +  res['support'].astype(str) + '\n Confidence = ' +  res['confidence'].astype(str) + '\n Conviction = ' +  res['conviction'].astype(str)
                        res_ant = res[['antecedents','antecedent support']].rename(columns={'antecedents': 'node', 'antecedent support': 'size'}) #[['antecedents','antecedent support']]
                        res_con = res[['consequents','consequent support']].rename(columns={'consequents': 'node', 'consequent support': 'size'}) #[['consequents','consequent support']]
                        res_node = pd.concat([res_ant, res_con]).drop_duplicates(keep='first')
                        return res_node, res
                     
                     res_node, res = map_node()

                     @st.cache_resource(ttl=3600)
                     def arul_network():
                        nodes = []
                        edges = []

                        for w,x in zip(res_node['size'], res_node['node']):
                            nodes.append( Node(id=x, 
                                            label=x,
                                            size=50*w+10,
                                            shape="circularImage",
                                            labelHighlightBold=True,
                                            group=x,
                                            opacity=10,
                                            mass=1,
                                            image="https://upload.wikimedia.org/wikipedia/commons/f/f1/Eo_circle_yellow_circle.svg") 
                                    )   

                        for y,z,a,b in zip(res['antecedents'],res['consequents'],res['confidence'],res['to']):
                            edges.append( Edge(source=y, 
                                            target=z,
                                            title=b,
                                            width=a*2,
                                            physics=True,
                                            smooth=True
                                            ) 
                                    )  
                        return nodes, edges

                     nodes, edges = arul_network()
                     config = Config(width=1200,
                                     height=800,
                                     directed=True, 
                                     physics=True, 
                                     hierarchical=False,
                                     maxVelocity=5
                                     )

                     return_value = agraph(nodes=nodes, 
                                           edges=edges, 
                                           config=config)
    with tab2:
        st.markdown('**Agrawal, R., Imieliński, T., & Swami, A. (1993). Mining association rules between sets of items in large databases. In ACM SIGMOD Record (Vol. 22, Issue 2, pp. 207–216). Association for Computing Machinery (ACM).** https://doi.org/10.1145/170036.170072')
        st.markdown('**Brin, S., Motwani, R., Ullman, J. D., & Tsur, S. (1997). Dynamic itemset counting and implication rules for market basket data. ACM SIGMOD Record, 26(2), 255–264.** https://doi.org/10.1145/253262.253325')
        st.markdown('**Edmonds, J., & Johnson, E. L. (2003). Matching: A Well-Solved Class of Integer Linear Programs. Combinatorial Optimization — Eureka, You Shrink!, 27–30.** https://doi.org/10.1007/3-540-36478-1_3') 
        st.markdown('**Li, M. (2016, August 23). An exploration to visualise the emerging trends of technology foresight based on an improved technique of co-word analysis and relevant literature data of WOS. Technology Analysis & Strategic Management, 29(6), 655–671.** https://doi.org/10.1080/09537325.2016.1220518')

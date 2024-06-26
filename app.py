# pip install streamlit langchain langchain-openai beautifulsoup4 python-dotenv chromadb elevenlabs

from elevenlabs.client import ElevenLabs
from elevenlabs import play, save
import streamlit as st
import pybase64
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders import TextLoader

client = ElevenLabs(
  api_key="sk_e2c9a969eb8688594bd1a6dd2f926381cad891828bf76168"
)

load_dotenv()

def get_vectorstore_from_url(url):
    # get the text in document form
    #loader = WebBaseLoader(url)
    #loader = TextLoader("C:/Users/kessl/Desktop/Chatbot/txt/Syllabi.txt")
    loader = WebBaseLoader("https://engineeringpf.hs-pforzheim.de/master/wirtschaftsingenieurwesen/engineering_and_management")
    document = loader.load()
    
    # split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter()
    document_chunks = text_splitter.split_documents(document)
    
    # create a vectorstore from the chunks
    vector_store = Chroma.from_documents(document_chunks, OpenAIEmbeddings())

    return vector_store

def get_context_retriever_chain(vector_store):
    llm = ChatOpenAI()
    
    retriever = vector_store.as_retriever()
    
    prompt = ChatPromptTemplate.from_messages([
      MessagesPlaceholder(variable_name="chat_history"),
      ("user", "{input}"),
      ("user", "Given the above conversation, generate a search query to look up in order to get information relevant to the conversation. If the information which has been asked for is not given please answer that they should get in contact with either Ansgar Kühn or Lisa Kaiser in order to get specific information.")
    ])
    
    retriever_chain = create_history_aware_retriever(llm, retriever, prompt)
    
    return retriever_chain
    
def get_conversational_rag_chain(retriever_chain): 
    
    llm = ChatOpenAI()
    
    prompt = ChatPromptTemplate.from_messages([
      ("system", "Answer the user's questions based on the below context:\n\n{context}"),
      MessagesPlaceholder(variable_name="chat_history"),
      ("user", "{input}"),
    ])
    
    stuff_documents_chain = create_stuff_documents_chain(llm,prompt)
    
    return create_retrieval_chain(retriever_chain, stuff_documents_chain)

def get_response(user_input):
    retriever_chain = get_context_retriever_chain(st.session_state.vector_store)
    conversation_rag_chain = get_conversational_rag_chain(retriever_chain)
    
    response = conversation_rag_chain.invoke({
        "chat_history": st.session_state.chat_history,
        "input": user_input
    })
    
    return response['answer']

# app config
st.set_page_config(page_title="Chat with websites", page_icon="🤖")
st.title("Chat with websites")

# sidebar
with st.sidebar:
    st.header("Settings")
    website_url = st.text_input("Website URL")

if website_url is None or website_url == "":
    st.info("Please enter a website URL")

else:
    # session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            AIMessage(content="Hallo, ich bin der MEM-Bot. Wie kann ich dir weiterhelfen?"),
        ]
        audio = client.generate(
            text = "Hallo, ich bin der MEM-Bot. Wie kann ich dir weiterhelfen?",
            voice = "Rachel",
            model = "eleven_multilingual_v2",
            output_format= "mp3_22050_32"
        )
        save(audio, "audio.mp3")

        def autoplay_audio(file_path: str):
            with open(file_path, "rb") as f:
                data = f.read()
                b64 = pybase64.b64encode(data).decode()
                md = f"""
                    <audio controls autoplay="true">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                    """
                st.markdown(
                    md,
                    unsafe_allow_html=True,
                )
        autoplay_audio("audio.mp3")
  
        #st.audio("audio.mp3", format = "audio/mp3", autoplay = True)
  
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = get_vectorstore_from_url(website_url)    

    # user input
    user_query = st.chat_input("Type your message here...")
    if user_query is not None and user_query != "":
        response = get_response(user_query)
        st.session_state.chat_history.append(HumanMessage(content=user_query))
        st.session_state.chat_history.append(AIMessage(content=response))
        voice_response = client.generate(
            text = response,
            voice = "Rachel",
            model = "eleven_multilingual_v2",
            output_format= "mp3_22050_32"
        )
        save(voice_response, "response.mp3")

        def autoplay_audio(file_path: str):
            with open(file_path, "rb") as f:
                data = f.read()
                b64 = pybase64.b64encode(data).decode()
                md = f"""
                    <audio controls autoplay="true">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                    """
                st.markdown(
                    md,
                    unsafe_allow_html=True,
                )
        autoplay_audio("response.mp3")
  
        #st.audio("response.mp3", format = "audio/mp3", autoplay = True)
       

    # conversation
    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.write(message.content)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.write(message.content)

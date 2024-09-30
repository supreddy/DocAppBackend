# text_processor.py
import os
from langchain_core.output_parsers import StrOutputParser
import chromadb

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.helper.template_loader import get_template_by_type

from langchain.prompts import PromptTemplate


# code to summarize link

llm = ChatOpenAI(
    model="gpt-3.5-turbo-0125",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # api_key=apikey,  # if you prefer to pass api key in directly instaed of using env vars
    # base_url="...",
    # organization="...",
    # other params...
)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant who is an expert at "
            "understanding and highlighting key points from a text,"
            "an expert in summarization and understanding any patterns "
            "in the text. Use formatting and bullet points to explain any"
            " response that you are sending for clarity. Try and preserve" 
            "the orginal formatting in the original text",
        ),
        ("human", "text for transformation :{text_to_transform}"
         "------Instruction for transformation :{instruction}"),
    ]
)
chain = prompt | llm | StrOutputParser()





def process_files_with_instruction(filenames, instruction):
    """
    Process a list of files according to the provided instruction.
    
    :param filenames: List of filenames to process.
     
    :return: Processed text as a single block.
    """
    content_blocks = []

    for filename in filenames:
        if not os.path.exists(filename):
            raise FileNotFoundError(f"The file {filename} does not exist.")
        
        with open(filename, 'r') as file:
            content = file.read()
            content_blocks.append(content)
    
    
    json_result= chain.invoke(
                {
                    "text_to_transform": content,
                    "instruction":instruction
                }
            )
 

    return json_result


 
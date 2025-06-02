#pip install google-genai, sqlite3 
import streamlit as st, pandas as pd, sqlite3, matplotlib.pyplot as plt, json, os, io
from google import genai
from google.genai import types



def generate_schema_from_csv(df):
    schema = {
        "table": [{
            "table_name": "data",  # generic name
            "schema": []
        }]
    }
    
    for col in df.columns:
        schema["table"][0]["schema"].append({
            "name": col,
            "type": infer_type(df[col]),
            "description": f"Column containing {col} data"
        })
    
    return json.dumps(schema)



def setup():
    st.markdown("""
        <style>
               /* Remove blank space at top and bottom */ 
               .block-container {
                   padding-top: 1rem;
                   padding-bottom: 0rem;
                }

        </style>
        """, unsafe_allow_html=True)
    st.title(":material/chat: :blue[Chat with your CSV data] :material/chat:")
    hide_menu_style = """
            <style>
            #MainMenu {visibility: hidden;}
            </style>
            """
    st.markdown(hide_menu_style, unsafe_allow_html=True)
    

def get_clear():
    clear_button=st.sidebar.button("Start new session", key="clear")
    return clear_button


def parse_data(response2):
        to_parse = response2.automatic_function_calling_history[2].parts[0].function_response.response
        result_string = to_parse['result']
        json_string = result_string.replace('```json\n', '').replace('\n', '').replace('```', '').strip()
        try:
            result_dict = json.loads(json_string)
            recommended_chart = result_dict.get('recommended_chart')
        except json.JSONDecodeError as e:
            st.write(f"Error decoding JSON: {e}")
            st.write(f"Problematic JSON string: '{json_string}'")
            st.stop()
        except KeyError:
            st.write("'recommended_chart' key not found in the parsed JSON.")
            st.stop()
            
        data=response2.automatic_function_calling_history[4].parts[0].function_response.response
        desired_string = data['result']

        return recommended_chart, desired_string


def get_query(prompt: str) -> str:
    """Retrieve sql query based on user prompt."""
    data = json.loads(schema2)
    table_name = data['table'][0]['table_name']
    
    sys_message = f"""
    Provide a sql code that will help answer user's following question: {prompt}. 
    You are an expert in answering questions users have about their data stored in sqlite3, 
    and recommending visualization types.  
    Your job is to execute the relevant SQL statements against sqlite3 tables to get the best answer. 
    The user is only interested in seeing the final result from sqlite3.
    
    1. If the user request is reasonable and compatible with the schema, YOU MUST FIRST call the `execute_query_tool2`to get the result.
        When generating the SQL query:
        Use meaningful aliases for column names.    
        Order results for clarity when appropriate. 
        Select only necessary columns; avoid SELECT *. 
        Use valid sqlite3 SQL. 
        Use only SELECT statements (no DML).    
    
    2. Call the `execute_query_tool2` tool to execute the generated SQL query. If the query fails, analyze the error message and attempt to correct the SQL.  If correction is not possible, inform the user of the error and its likely cause.
    
    3. Suggest an appropriate chart type for visualizing the query results, if applicable. 
    
    4. Only once you have the result from sqlite3, present the final results to the user and terminate the conversation. Do not call any other tools after this.
    
    You will use the following schema for all queries and all SQL must conform to this schema: {schema2}.   
    
    Here are examples to guide your query generation and visualization recommendation:
    **Example Question 1:**
    If a user asks: 'how many total loans are there?' you should return back:
    'SELECT count (distinct Loan_ID) FROM {table_name}' 
    Recommended Chart: None (The result is a single numeric value.) 
    
    **Example Question 2:**
    If a user asks: 'what are the total number of loans for each education level?' you should return back:
    'SELECT education, count(*) as number_loans FROM {table_name} group by education'
    Recommended Chart: Bar chart (Education on the X-axis and number_loans on the Y-axis.)
    
    **Example Question 3:**
    If a user asks: 'Give me a breakdown of the loans by gender' you should return back:
    'SELECT gender, count(*) as number_of_loans FROM {table_name} group by gender'
    Recommended Chart: Bar chart (Gender on the X-axis and number_of_loans on the Y-axis.)
    
    **Example Question 4:**
    If a user asks: 'What percent of loans are paid off?' you should return back:
    'SELECT loan_status, (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table_name})) as percentage FROM {table_name} GROUP BY loan_status'
    Recommended Chart: Pie chart (Show each loan_status's percentage of the total.)
    
    **Example Question 5:**
    If a user asks: 'list all loans with a principal amount greater than 10000' you should return back:
    'SELECT Loan_ID FROM {table_name} where Principal>10000'
    Recommended Chart: None (The result is a list of loans that have a principal greater than 10000.)
    
    **Example Question 6:**
    If a user asks: 'what is the average loan amount for borrowers over 40 and under 40?' you should return back:
    'SELECT  (CASE WHEN age <= 40 THEN '<= 40' ELSE '> 40' END) AS age_group, avg(Principal) as average_loan_amount FROM {table_name} group by age_group'
    Recommended Chart: Bar chart (age_group on the X-axis and average_loan_amount on the Y-axis.) 
    
    **Example Question 7:**
    If a user asks: 'what is the average loan amount based on the borrowers due date?' you should return back:
    'SELECT FORMAT_DATE("%Y-%m-%d",due_date) as formatted_date, avg(Principal) as average_loan_amount FROM {table_name} group by due_date order by due_date'
    Recommended Chart: Line chart (formatted_date on the X-axis and average_loan_amount on the Y-axis.) 
    
    **Example Question 8:**
    If a user asks: 'what is the distibution of loans by effective date?' you should return back:
    'SELECT FORMAT_DATE("%Y-%m-%d", effective_date) as formatted_date, count(*) as number_of_loans FROM {table_name} group by effective_date order by effective_date'
    Recommended Chart: Line chart (formatted_date on the X-axis and number_of_loans on the Y-axis.)
    
    If query has to use a datetime date, make sure to return the date as a string.     
    
    Double check that you are only using fields that are listed in the schema {schema2}.  Go back and correct if you the field names don't conform to this schema. 
    Return the result in a json format that has two keys: query and recommended_chart, and the only values allowed for recommended_chare are Bar, Line, Pie, or None. 
    """
    
    chat = client.chats.create(model='gemini-2.0-flash')
    response = chat.send_message(f"{sys_message}")
    return response.text


def execute_query_tool(query: str) -> str:
    """Execute a SQL query against Sqlite3 and return the results as a JSON string."""

    try:
      result = pd.read_sql_query(query, conn)
      data = str(json.dumps(result.to_string()))
      return data
    except Exception as e:
      error_message = f"Sqlite Query Error: {str(e)}"
      st.stop()
      return json.dumps({"Sqlite Query error": error_message})
  

def get_chart(data, charttype):
    cleaned_data = data.strip('"').replace('\\n', '\n')
    dfa = pd.read_csv(io.StringIO(cleaned_data), sep=r'\s+')
    
    if charttype == "Bar":
        if dfa.shape[-1] < 2:
            print("DataFrame does not have at least two columns to plot.")
        else:
            plt.figure(figsize=(8, 6))
            plt.bar(dfa.iloc[:, 0], dfa.iloc[:, 1], color=['skyblue'])
            plt.xlabel(dfa.columns[0])
            plt.ylabel(dfa.columns[1])
            plt.title(f"{dfa.columns[1]} by {dfa.columns[0]}")
            plt.xticks(dfa.iloc[:, 0])
            plt.grid(axis='y', linestyle='--')
            plt.tight_layout()
            st.pyplot(plt.gcf())
    elif charttype == "Pie":
        if dfa.shape[-1] < 2:
            st.write("DataFrame does not have at least two columns to plot.")
            st.stop()
        elif len(dfa.iloc[:, 1]) != len(dfa.iloc[:, 0]):
            st.write("Number of labels and values must be the same for a pie chart.")
            st.stop()
        elif not pd.api.types.is_numeric_dtype(dfa.iloc[:, 1]):
            st.write("The second column must contain numeric data for the pie chart values.")
            st.stop()
        else:
            plt.figure(figsize=(8, 8)) 
            labels = dfa.iloc[:, 0]
            sizes = dfa.iloc[:, 1]
            plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
            plt.title(f"Distribution of {dfa.columns[1]} by {dfa.columns[0]}")
            plt.axis('equal') 
            plt.tight_layout()
            st.pyplot(plt.gcf())
    elif charttype == "Line":
        if dfa.shape[-1] < 2:
            st.write("DataFrame does not have at least two columns to plot.")
            st.stop()
        elif not pd.api.types.is_numeric_dtype(dfa.iloc[:, 1]):
            st.write("The second column must contain numeric data for the line chart values.")
            st.stop()
        else:
            plt.figure(figsize=(10, 6))
            plt.plot(dfa.iloc[:, 0], dfa.iloc[:, 1], marker='o', linestyle='-')
            plt.xlabel(dfa.columns[0])
            plt.ylabel(dfa.columns[1])
            plt.title(f"{dfa.columns[1]} by {dfa.columns[0]}")
            plt.grid(True, linestyle='--')
            plt.tight_layout()
            st.pyplot(plt.gcf())
    elif charttype == "None":
        st.write("Nothing to plot.")


def main():
    filename = st.sidebar.text_input("Provide path to CSV file:")
    if filename:
        df = pd.read_csv(filename)
        t_name = json.loads(schema2)
        table_name = t_name['table'][0]['table_name']
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        clear = get_clear()
        if clear:
            if 'message' in st.session_state:
                del st.session_state['message']
    
        if 'message' not in st.session_state:
            st.session_state.message = " "
        
        if clear not in st.session_state:
            system_instruction="""You are provided the user's prompt. you are also provided the 
                               data you need to answer the question. take these 2 pieces of information 
                               to formulate a concise, meaningful, and user friendly resposne for the 
                               user. Think step by step as you construct the final response for 
                               the user."""
            config = {
                       "tools": [get_query, execute_query_tool],
                       'temperature': 0,
                       "system_instruction": system_instruction,
                     }
            chat = client.chats.create(model=MODEL_ID, config=config,)
            prompt = st.chat_input("Enter your question here")
            if prompt:
                with st.chat_message("user"):
                    st.write(prompt)
                st.session_state.message += prompt
                
                with st.chat_message(
                    "model", avatar="🧞‍♀️",
                ):
                    response = chat.send_message(st.session_state.message)
                    st.markdown(response.text) 
                    st.divider()
                    chart_type, data = parse_data(response)
                    get_chart(data, chart_type)
                    st.sidebar.markdown(response.usage_metadata)
                st.session_state.message += response.text
        

if __name__ == "__main__":
    setup()
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    client = genai.Client(api_key = GOOGLE_API_KEY)
    MODEL_ID = "gemini-2.0-flash-001"
    conn = sqlite3.connect(':memory:')
    main()
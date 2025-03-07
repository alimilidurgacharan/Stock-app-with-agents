from flask import Flask, render_template, request, jsonify
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from dotenv import load_dotenv
import os
import markdown # type: ignore
import re
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import yfinance as yf
from io import BytesIO
import datetime
from datetime import datetime
matplotlib.use('Agg')

load_dotenv()
groq_api = os.getenv('Groq_API_KEY')

app = Flask(__name__)

stock_analysis_agent = Agent(
    name='Stock Analysis Agent',
    model=Groq(id="deepseek-r1-distill-llama-70b", api_key=groq_api),
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True),
        DuckDuckGoTools()
    ],
    instructions=[
        "Collect the Latest Stock Data",
        "Analyze the stock data, news, and provide recommendations (Buy, Hold, Sell).",
        "Ensure output is structured in a clean format with key insights."
    ],
    show_tool_calls=True,
    markdown=True
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    ticker = request.form.get('ticker')
    if not ticker:
        return jsonify({'error': 'Please enter a stock ticker.'})


    try:
        structured_prompt = f"""
    Collect stock data for {ticker}, analyze recent news, and provide insights including:
    
    - Historical stock prices, volume changes, and performance for the last month.
    - Key financial indicators such as moving averages, volatility, and momentum.
    - Provide a recommendation (Buy, Hold, Sell) based on the analysis.
    """
        response = stock_analysis_agent.run(structured_prompt)
        # print(response)
        # Check if the response contains the required information
        if hasattr(response, "content") and isinstance(response.content, str):
            analysis_content = response.content

            # Fetch stock data for the past month
            stock_data = yf.Ticker(ticker)
            history = stock_data.history(period="1y")
            plot_url = generate_stock_graph(history)

            disclaimer = (
                "<div class='alert alert-warning'>Disclaimer: The stock analysis and recommendations provided "
                "are for informational purposes only and should not be considered financial advice. Always do your "
                "own research or consult with a financial professional.</div>"
            )

            # Process the agent response (markdown, table, analysis)
            markdown_content = markdown.markdown(analysis_content)
            formatted_response = re.sub(r'<table>', '<table class="table table-bordered table-striped">', markdown_content)

            return jsonify({
                'result': formatted_response,
                'graph': plot_url,
                'disclaimer': disclaimer
            })
        else:
            return jsonify({'error': 'Unexpected response format from AI agent.'})

    except Exception as e:
        return jsonify({'error': f'Error processing request: {str(e)}'})
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO

def generate_stock_graph(history):
    plt.figure(figsize=(10, 6))
    sns.set(style="darkgrid")

    # Plot stock closing price
    plt.plot(history.index, history['Close'], label="Closing Price", color='b')
    plt.title('Stock Price - Last 1 Month')
    plt.xlabel('Date')
    plt.ylabel('Price (USD)')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()

    # Save plot to a BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)

    # Encode the image to base64
    encoded_img = base64.b64encode(img.getvalue()).decode("utf-8")

    plt.close()
    return f"data:image/png;base64,{encoded_img}"



# import plotly.express as px
# import plotly.io as pio
# from io import BytesIO
# import pandas as pd

# def generate_stock_graph(history):
#     fig = px.line(history, x=history.index, y='Close', title='Stock Price - Last 1 Month', 
#                   labels={'Close': 'Price (USD)', 'index': 'Date'})
#     fig.update_traces(line=dict(color='blue'), name="Closing Price")
#     fig.update_layout(xaxis_title='Date', yaxis_title='Price (USD)', xaxis_tickangle=-45)
    
#     # Save plot to a BytesIO object
#     img = BytesIO()
#     pio.write_image(fig, img, format='png')
#     img.seek(0)
    
#     # Save the image to a file
#     img_url = '/static/stock_graph.png'
#     with open('static/stock_graph.png', 'wb') as f:
#         f.write(img.read())
    
#     return img_url


if __name__ == "__main__":
    app.run(debug=True)

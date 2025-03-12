from flask import Flask, render_template, request, jsonify
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
import os
import re
import yfinance as yf
import markdown
from dotenv import load_dotenv
import json

load_dotenv()

groq_api = os.getenv('GROQ_API_KEY')

app = Flask(__name__)

# Define Stock Analysis Agent
stock_analysis_agent = Agent(
    name='Stock Analysis Agent',
    model=Groq(id="deepseek-r1-distill-llama-70b", api_key=api_key
               ),
    tools=[
        YFinanceTools(stock_price=True, analyst_recommendations=True, company_info=True),
        DuckDuckGoTools()
    ],
    instructions=[
        "Use DuckDuckGoTools for real-time stock-related news.",
        "Use YFinanceTools for stock prices, company details, and analyst recommendations.",
        "Provide top 3 recent news headlines with short summaries.",
    ],
    show_tool_calls=False,
    markdown=True
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    ticker = request.form.get('ticker').strip().upper()
    if not ticker:
        return jsonify({'error': 'Please enter a valid stock ticker.'})
    
    try:
        stock_data = yf.Ticker(ticker)
        stock_info = stock_data.info

        # Fetch real-time stock price
        current_price = stock_info.get('regularMarketPrice', None)
        after_hours_price = stock_info.get('postMarketPrice', None)
        previous_close = stock_info.get('previousClose', None)

        # Handle missing real-time price
        if current_price is None:
            current_price = previous_close

        # Construct stock price message
        price_message = f"📊 **Live Stock Price**: ${current_price:.2f}" if current_price is not None else "📊 **Stock Price Unavailable**"
        if after_hours_price:
            price_message += f"\n📉 **After-Hours Price**: ${after_hours_price:.2f}"

        structured_prompt = f"""
        You are a **Stock Analysis AI**. Your job is to analyze **{ticker}** and generate a structured stock report every time, following this exact format:

        📌 **Instructions**:
        - Use **YFinanceTools** to get:
        - **Real-time stock price**
        - **Company details (market cap, sector, key financials)**
        - **Analyst recommendations**
        - **Latest stock news**
        - **Technical analysis & trends**
        - **Follow this format exactly for every report**:

        - Do NOT use DuckDuckGo for stock prices. Only use it for real-time stock-related news.
        - If real-time price is missing, use the last closing price with a note: "**Note: Real-time price data unavailable. Using last closing price instead.**"
        - Ensure the response is in **clean Markdown format** without any extraneous information.
        - Ensure the **Recent News** section always follows this exact format with numbered news items, headlines, summaries, and sources as a website links.
        - Ensure the **Recent News** summary should be minimun of 3 lines.

        Strictly Return your response in **clean Json format**.
        Dont change any key values in the json.and also dont include any other keys.

        Expected json format::

        {{
            "Company Overview": {{
                "Market Cap": ""
                "Sector": ""
                "Industry": ""
                "Key Financials":{{
                    "Revenue (TTM)": ""
                    "Net Income (TTM)": ""
                    "EPS (TTM)": ""
                }}
            }},
            "Stock Performance": {{
                {price_message}
                "52-Week Range" : ""
                "Volume (Avg.)" : ""
                "Market Cap" : ""
            }},
            "Recent News": [
            {{
                "News 1" : ""
                "Summary" : ""
                "Source" : ""
            }},
            {{
                "News 2" : ""
                "Summary" : ""
                "Source" : ""
            }},
            {{
                "News 3" : ""
                "Summary" : ""
                "Source" : ""
            }}],
            "Analyst Ratings" : {{
                "Analyst Consensus" : "",
                "Average Price Target" : ""
                "Breakdown:" {{
                    "Buy Percentage" : ""
                    "Hold Percentage" : ""
                    "Sell Percentage" : ""
                }}
            }},
            "Technical Trend Analysis" : {{
                "50-Day Moving Average" : ""
                "200-Day Moving Average" : ""
                "RSI" : ""
                "MACD" : ""
            }},
            "Final Buy/Hold/Sell Recommendation" : {{
                "Recommendation" : ""
                "Reasoning" : ""
            }}
        }}
        Note: please dont display any other information outoff the json response
        """

        # Run the agent with the structured prompt
        response = stock_analysis_agent.run(structured_prompt)
        analysis_content = response.content if hasattr(response, "content") else "No analysis available."
        
        # If content is missing, use default/fallback text
        analysis_content = re.sub(r"Not explicitly provided in the tool output.", "Not available but will continue fetching other relevant data...", analysis_content).strip()

        # Fetch stock history for plots
        history = stock_data.history(period="3mo")
        if history.empty:
            return jsonify({'error': f'No stock data found for {ticker}.'})

        plot_data = {
            'dates': history.index.strftime('%Y-%m-%d').tolist(),
            'open': history['Open'].tolist(),
            'high': history['High'].tolist(),
            'low': history['Low'].tolist(),
            'close': history['Close'].tolist(),
            'volume': history['Volume'].tolist()
        }

        disclaimer = (
            "<div class='alert alert-warning'>Disclaimer: The stock analysis and recommendations provided "
            "are for informational purposes only and should not be considered financial advice. Always do your "
            "own research or consult with a financial professional.</div>"
        )

        # Replace missing data with placeholders or specific fallbacks
        analysis_content = analysis_content.replace("Not explicitly provided in the tool output.", "Data will be updated with the closest available info.")
        try:
            # First clean up the JSON string - remove markdown code blocks if present
            json_string = re.sub(r'```json|```', '', analysis_content).strip()
            
            # Parse the JSON
            stock_data_json = json.loads(json_string)
            
            # Now convert JSON to formatted text with HTML headings
            formatted_text = """
            <style>
                .container {
                    display: flex;
                    gap: 30px;
                    justify-content: space-between;
                    flex-wrap: wrap;
                }
                .box {
                    border: 1px solid #ccc;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
                    flex: 1 1 calc(25% - 20px); /* Adjust width for 4 in a row */
                    min-width: 250px;
                    text-align: center;
                    box-sizing: border-box;
                }
                h2, h3 {
                    text-align: center;
                }
            </style>
            <div class="container">
            """

            # Company Overview
            formatted_text += """
                <div class="box">
                    <h2>COMPANY OVERVIEW</h2>
                    <p><strong>Market Cap:</strong> {}</p>
                    <p><strong>Sector:</strong> {}</p>
                    <p><strong>Industry:</strong> {}</p>
                </div>
            """.format(
                stock_data_json.get('Company Overview', {}).get('Market Cap', 'N/A'),
                stock_data_json.get('Company Overview', {}).get('Sector', 'N/A'),
                stock_data_json.get('Company Overview', {}).get('Industry', 'N/A')
            )

            # Key Financials
            financials = stock_data_json.get('Company Overview', {}).get('Key Financials', {})
            formatted_text += """
                <div class="box">
                    <h2>Key Financials</h2>
                    <p><strong>Revenue (TTM):</strong> {}</p>
                    <p><strong>Net Income (TTM):</strong> {}</p>
                    <p><strong>EPS (TTM):</strong> {}</p>
                </div>
            """.format(
                financials.get('Revenue (TTM)', 'N/A'),
                financials.get('Net Income (TTM)', 'N/A'),
                financials.get('EPS (TTM)', 'N/A')
            )

            # Stock Performance
            perf = stock_data_json.get('Stock Performance', {})
            formatted_text += """
                <div class="box">
                    <h2>STOCK PERFORMANCE</h2>
            """
            for key, value in perf.items():
                formatted_text += f"<p><strong>{key}:</strong> {value}</p>"

            formatted_text += "</div>"

            # Analyst Ratings & Technical Trend Analysis
            ratings = stock_data_json.get('Analyst Ratings', {})
            tech = stock_data_json.get('Technical Trend Analysis', {})
            formatted_text += """
                <div class="box">
                    <h2>ANALYST RATINGS & TECHNICAL TREND ANALYSIS</h2>
                    <p><strong>Analyst Consensus:</strong> {}</p>
                    <p><strong>Average Price Target:</strong> {}</p>
            """.format(
                ratings.get('Analyst Consensus', 'N/A'),
                ratings.get('Average Price Target', 'N/A')
            )

            for key, value in tech.items():
                formatted_text += f"<p><strong>{key}:</strong> {value}</p>"

            formatted_text += """
                </div>
            </div>
            """



            # Recent News
            formatted_text += "<h2>RECENT NEWS</h2>"
            for i, news in enumerate(stock_data_json.get('Recent News', []), 1):
                formatted_text += f"<h3>News {i}</h3>"
                formatted_text += f"<p><strong>Summary:</strong> {news.get('Summary', 'N/A')}</p>"
                
                # Add detailed information if available
                if 'Detailed Summary' in news:
                    formatted_text += f"<p><strong>Detailed Summary:</strong> {news.get('Detailed Summary', 'N/A')}</p>"
                
                # Make source a hyperlink
                source_name = news.get('Source', 'N/A')
                source_link = news.get('Source Link', '#')
                formatted_text += f'<p><strong>Source:</strong> <a href="{source_link}" target="_blank">{source_name}</a></p>'

            
            # Final Recommendation
            formatted_text += "<h2>FINAL BUY/HOLD/SELL RECOMMENDATION</h2>"
            rec = stock_data_json.get('Final Buy/Hold/Sell Recommendation', {})
            formatted_text += f"<p><strong>Recommendation:</strong> {rec.get('Recommendation', 'N/A')}</p>"
            formatted_text += f"<p><strong>Reasoning:</strong> {rec.get('Reasoning', 'N/A')}</p>"
            
            # Replace the markdown processing with our formatted text
            formatted_response = formatted_text
    
        except json.JSONDecodeError as e:
            # If JSON parsing fails, keep the original content but clean it
            print(f"JSON parsing error: {e}")
            # Your existing markdown processing as fallback
            markdown_content = markdown.markdown(analysis_content)
            cleaned_content = re.sub(r'```.*?```', '', markdown_content, flags=re.DOTALL)
            cleaned_content = re.sub(r"</?p>|</code>|<code>|>", "", cleaned_content)
            formatted_response = re.sub(r'<table>', '<table class="table table-bordered table-striped">', cleaned_content)

        return jsonify({
            'result': formatted_response,  # Plain text
            'raw_json': stock_data_json,   # Original JSON data
            'plot_data': plot_data,
            'disclaimer': disclaimer
        })
    except Exception as e:
        return jsonify({'error': f'Error processing request: {str(e)}'})

if __name__ == "__main__":
    app.run(debug=True)

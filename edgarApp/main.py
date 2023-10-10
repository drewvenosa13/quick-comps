import sys
sys.path.append("c:/Users/drewv/Downloads/__pycache__/edgarAPI/edgarApp")
import apiCall as apiCall
from flask import Flask, render_template, make_response, flash, session, request, redirect, url_for, jsonify
import pandas as pd
import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

os.environ['GOOGLE_APPLICATION_CREDENTIALS']= os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

BUCKET_NAME=os.getenv('BUCKET_NAME')
print(BUCKET_NAME)
client = storage.Client()

bucket = client.bucket(BUCKET_NAME)

app = Flask(__name__)
app.config["SECRET_KEY"] = "some_random_string"


@app.route('/api/tickers', methods=['GET'])
def get_tickers():
    tickers_and_names = [{"ticker": row["Symbol"], "name": row["Security"]} for _, row in apiCall.tickerdf.iterrows()]
    return jsonify(tickers_and_names)

@app.route('/api/cik', methods=['GET'])
def get_cik():
    ticker = request.args.get('ticker', None)
    if not ticker:
        return jsonify({"error": "Ticker parameter is missing."}), 400
    cik = apiCall.tickerdf.loc[apiCall.tickerdf['Symbol'] == ticker, 'CIK'].iloc[0]
    return jsonify({"cik": cik})




@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        userTicker = request.form['ticker'].upper()

        # Check if ticker is in the DataFrame
        if userTicker not in apiCall.tickerdf['Symbol'].values:
            flash('Please select a stock in the S&P 500', 'error')
            return redirect(url_for('index'))
        userTickerName = apiCall.tickerdf.loc[apiCall.tickerdf['Symbol'] == userTicker, 'Security'].iloc[0]
        userTickerCIK = apiCall.tickerdf.loc[apiCall.tickerdf['Symbol'] == userTicker, 'CIK'].iloc[0]
        # Check if ticker is valid
        apiCall.tickerCheck(userTicker)
        
        # Retrieve possible competitors
        competitors = apiCall.competitorCheck(userTicker)


        # Pre-process data
        competitors_data = []
        for competitor in competitors:
            competitors_data.append({
                'ticker': competitor,
                'name': apiCall.tickerdf.loc[apiCall.tickerdf['Symbol'] == competitor, 'Security'].iloc[0],
                'cik': apiCall.tickerdf.loc[apiCall.tickerdf['Symbol'] == competitor, 'CIK'].iloc[0]
            })


        # Pass pre-processed data to the template
        return render_template("competitors.html", userTicker=userTicker, userTickerName=userTickerName, userTickerCIK=userTickerCIK, competitors=competitors_data, maxComparisons=apiCall.maxComparisons)
    
    return render_template("index.html")

@app.route("/generate_excel", methods=["POST"])
def generate_excel():
    userTicker = request.form['userTicker']

    # Building the selected_comparisons list
    selected_comparisons = [{'Ticker': userTicker, 
                             'Name': apiCall.tickerdf.loc[apiCall.tickerdf['Symbol'] == userTicker, 'Security'].iloc[0],
                             'CIK': apiCall.tickerdf.loc[apiCall.tickerdf['Symbol'] == userTicker, 'CIK'].iloc[0]}]

    for competitor in request.form.getlist('competitor'):
        ticker, name, cik = competitor.split('|')
        selected_comparisons.append({'Ticker': ticker, 'Name': name, 'CIK': cik})

    # Retrieving the GAAP statements for selected comparisons
    gaap_statements_results = apiCall.get_gaap_statements_for_cik_list(selected_comparisons)

    # Creating a list of dictionaries containing data for each ticker
    data_list = []
    for ticker_info in selected_comparisons:
        ticker_data = {"companyName": ticker_info['Name'], "companyTicker": ticker_info['Ticker']}

        gaapStatements = gaap_statements_results[ticker_info['Ticker']]
    
        for key in apiCall.keys_of_interest:
                value = gaapStatements.get(key,'N/A')
                ticker_data[key] = value

        data_list.append(ticker_data)
        print(ticker_data)
        print(data_list)


    # Generate the Excel file
    df = apiCall.generate_excel(pd.DataFrame(data_list), userTicker)

    # Return the filename to the template for download
    return render_template("download.html", filename=df)




@app.route("/download_file/<filename>")
def download_file(filename):
    # Get the blob from GCS
    blob = bucket.blob(filename)
    
    # Check if blob exists
    if not blob.exists():
        return "File not found", 404

    # Create a response
    output = blob.download_as_bytes()
    response = make_response(output)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return response



if __name__ == "__main__":
    app.run(debug=True)

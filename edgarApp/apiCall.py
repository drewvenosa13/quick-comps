import requests
import os
import pandas as pd
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

os.environ['GOOGLE_APPLICATION_CREDENTIALS']= os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

BUCKET_NAME=os.getenv("BUCKET_NAME")
client = storage.Client()


bucket = client.bucket(BUCKET_NAME)

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# Constants
headers = {'User-Agent': "drewvenosa13@outlook.com"}
maxComparisons = 5
maxMetrics = 5
keys_of_interest = keys_of_interest = ['MarketCapitalization', 'ReturnOnEquityTTM', 'ProfitMargin', 'ForwardPE', 'EVToEBITDA', 'PEGRatio']


website = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
tickerdf = website[0]
tickerdf['CIK'] = tickerdf['CIK'].astype(str).str.zfill(10)

# Check if ticker exists in the dataframe
def tickerCheck(userTicker):
    if userTicker in tickerdf['Symbol'].values:
        companyName = tickerdf.loc[tickerdf['Symbol'] == userTicker.upper(), 'Security'].iloc[0]
        companyCIK = tickerdf.loc[tickerdf['Symbol'] == userTicker.upper(), 'CIK'].iloc[0]
        companySubIndustry = tickerdf.loc[tickerdf['Symbol'] == userTicker.upper(), 'GICS Sub-Industry'].iloc[0]

        print(f'{userTicker} found: {companyName} CIK = {companyCIK}, SubIndustry = {companySubIndustry}')
    else:
        print('Ticker not found.')

def competitorCheck(userTicker):
    """Return a list of tickers in the same sub-industry as the given ticker."""
    
    # Get sub-industry of the user's ticker
    if userTicker in tickerdf['Symbol'].values:
        companySubIndustry = tickerdf.loc[tickerdf['Symbol'] == userTicker, 'GICS Sub-Industry'].iloc[0]
        
        # Retrieve other companies in the same sub-industry
        same_subindustry_df = tickerdf[tickerdf['GICS Sub-Industry'] == companySubIndustry]
        same_subindustry_df = same_subindustry_df[same_subindustry_df['Symbol'] != userTicker] # Exclude the user's ticker
        print(f"Found competitors for {userTicker}: {same_subindustry_df['Symbol'].tolist()}")
        
        return same_subindustry_df['Symbol'].tolist()
    else:
        return []
def compareTickers(userTicker, maxComparisons):
    """Prompt user to compare the given ticker with others in the same sub-industry."""
    
    industryTickers = competitorCheck(userTicker)
    userTickerName = tickerdf.loc[tickerdf['Symbol'] == userTicker, 'Security'].iloc[0]
    userTickerCIK = tickerdf.loc[tickerdf['Symbol'] == userTicker, 'CIK'].iloc[0]
    
    userTickers = [{'Ticker': userTicker, 'Name': userTickerName, 'CIK': userTickerCIK}]

    if industryTickers:
        comparisons = 0
        for ticker in industryTickers:
            if comparisons >= maxComparisons:
                break
            compare = input(f'Would you like to compare {userTicker.upper()} to {ticker}? (Y/N): ')
            if compare.upper() == 'Y':
                tickerName = tickerdf.loc[tickerdf['Symbol'] == ticker, 'Security'].iloc[0]
                tickerCIK = tickerdf.loc[tickerdf['Symbol'] == ticker, 'CIK'].iloc[0]
                
                userTickers.append({
                    'Ticker': ticker,
                    'Name': tickerName,
                    'CIK': tickerCIK
                })
                
                print(f'Comparing {userTicker.upper()} to {ticker}')
                comparisons += 1
        print('No more tickers selected for comparison.')
    else:
        print('No industry tickers found for comparison.')

    return userTickers
def get_overview_for_ticker(ticker):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
    print(f"Fetching data for {ticker} from {url}")  # Add this
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve data for {ticker}. Response Code: {response.status_code}")  # And this
        return {}
    data = response.json()
    print(f"Data received for {ticker}: {data}")

    # Extract relevant keys
    relevant_data = {
        'MarketCapitalization': data.get('MarketCapitalization', None),
        'ReturnOnEquityTTM': data.get('ReturnOnEquityTTM', None),
        'ProfitMargin': data.get('ProfitMargin', None),
        'ForwardPE': data.get('ForwardPE', None),
        'EVToEBITDA': data.get('EVToEBITDA', None),
        'PEGRatio': data.get('PEGRatio', None)
    }

    return relevant_data

def get_gaap_statements_for_cik_list(selected_comparisons):
    gaap_statements_dict = {}

    for ticker_info in selected_comparisons:
        ticker = ticker_info['Ticker']
        relevant_data = get_overview_for_ticker(ticker)
        gaap_statements_dict[ticker] = relevant_data

    return gaap_statements_dict

def generate_excel(df, userTicker):
    # Get the current maximum count from GCS
    blobs = list(bucket.list_blobs(prefix=f"{userTicker}CompAnalysis"))
    current_count = len(blobs)
    excel_file_name = f"{userTicker}CompAnalysis{current_count + 1}.xlsx"
    print(df)
    df.to_excel(excel_file_name, index=False)
    
    # Upload the file to GCS
    blob = bucket.blob(excel_file_name)
    blob.upload_from_filename(excel_file_name)

    # Delete the local copy (Optional)
    os.remove(excel_file_name)

    return excel_file_name

def main():
    userTicker = input('Enter your ticker here: ').upper()
    tickerCheck(userTicker)
    selected_comparisons = compareTickers(userTicker, maxComparisons)
    
    gaap_statements_results = get_gaap_statements_for_cik_list(selected_comparisons)

    # Print GAAP Statements Results
    for ticker, gaapStatements in gaap_statements_results.items():
        print(f"Data for {ticker}:")
        for key, value in gaapStatements.items():
            if key in keys_of_interest:  # Only show data for keys of interest
                print(f"{key}: {value}")
        print("\n")

    # Create DataFrame
    data_list = []
    for ticker_info in selected_comparisons:
        ticker_data = {"companyName": ticker_info['Name'], "companyTicker": ticker_info['Ticker']}
        print(f"Processing data for {ticker_info['Ticker']}")
        print(ticker_data)
        gaapStatements = gaap_statements_results[ticker_info['Ticker']]

        for key, value in gaapStatements.items():
            if key in keys_of_interest:
                ticker_data[key] = value
        data_list.append(ticker_data)


    df = pd.DataFrame(data_list)
    print(df)
    excel_file_name = generate_excel(df, userTicker)
    
    print(f"Data saved to {excel_file_name}")
    
    # Optional: Provide a mechanism to download the file
    prompt = input("Do you want to open the directory containing the file? (Y/N): ").upper()
    if prompt == 'Y':
        os.system(f'explorer.exe /select,"{os.path.abspath(excel_file_name)}"')
    
if __name__ == '__main__':
    main()

if __name__ == '__main__':
    main()
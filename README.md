# quick-comps
This is a website meant to help with making a comparable analysis table for companies in the S&P 500. It's built in Python using the AlphaVantage API and Google Cloud. 

User is prompted to enter a ticker in the S&P 500. They're then prompted to select from a list of that ticker's competitors. I pulled competitor info off this site: 
https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
and based it off the GICS Sub-Sector. 

Once they select from that list of tickers, they're able to download an Excel spreadsheet containing each company's: 
Name
Ticker
MarketCap
ForwardPE
PEGRatio
EV/EBITDA
ROE-TTM

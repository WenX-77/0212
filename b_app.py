from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
import matplotlib.pyplot as plt
import os

app = Flask(__name__)

# Alpha Vantage API Key
API_KEY = "YOUR_API_KEY"

def get_stock_news_sentiment(ticker, api_key, news_count=20):
    """
    Fetch recent news for a given stock and return title, URL, sentiment score, and relevance score.
    """
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&limit={news_count}&apikey={api_key}"
    
    response = requests.get(url)
    data = response.json()
    
    if "feed" in data:
        news_list = data["feed"][:news_count]  # Get the latest 'news_count' articles
        
        news_data = []
        for news in news_list:
            title = news.get("title", "N/A")
            url = news.get("url", "N/A")
            sentiment_score = float(news.get("overall_sentiment_score", 0))  # Overall sentiment score of the article
            relevance_score = float(news.get("relevance_score", 0.5))  # Overall relevance score (default: 0.5 if missing)

            # Extract ticker-specific sentiment score
            ticker_sentiment_score = 0
            ticker_relevance_score = 0
            for sentiment in news.get("ticker_sentiment", []):
                if sentiment["ticker"] == ticker:
                    ticker_sentiment_score = float(sentiment.get("ticker_sentiment_score", 0))
                    ticker_relevance_score = float(sentiment.get("relevance_score", 0.5))
                    break  # Stop loop after finding data for the specified ticker
            
            # Use ticker sentiment score if available
            final_sentiment_score = ticker_sentiment_score if ticker_relevance_score > 0 else sentiment_score

            news_data.append({
                "title": title,
                "url": url,
                "sentiment_score": final_sentiment_score,
                "relevance_score": ticker_relevance_score if ticker_relevance_score > 0 else relevance_score
            })
        
        df = pd.DataFrame(news_data)
        return df
    else:
        print(" Unable to fetch news data. Please check the API key or stock ticker.")
        return pd.DataFrame()

def calculate_weighted_sentiment(df):
    """
    Compute the weighted sentiment score (weighted by relevance).
    """
    if df.empty:
        return 0  # Return 0 if no data is available
    
    weighted_sum = (df["sentiment_score"] * df["relevance_score"]).sum()
    relevance_sum = df["relevance_score"].sum()

    return weighted_sum / relevance_sum if relevance_sum != 0 else 0

def generate_sentiment_plot(df, ticker):
    """
    Generate a scatter plot for sentiment analysis and save as an image.
    """
    if df.empty:
        return None

    SENTIMENT_THRESHOLD = 0.1
    RELEVANCE_THRESHOLD = 0.5

    # 计算加权情感分数
    weighted_sentiment_score = calculate_weighted_sentiment(df)

    plt.figure(figsize=(8, 6))

    # 颜色规则
    colors = ['red' if (s > SENTIMENT_THRESHOLD and r > RELEVANCE_THRESHOLD) else 'blue' 
              for s, r in zip(df["sentiment_score"], df["relevance_score"])]

    # 绘制散点图
    plt.scatter(df["relevance_score"], df["sentiment_score"], c=colors, alpha=0.7, edgecolors='k', label="News Data")

    # 添加阈值线
    plt.axhline(y=SENTIMENT_THRESHOLD, color='gray', linestyle='--', linewidth=1, label=f"Sentiment Threshold: {SENTIMENT_THRESHOLD}")  
    plt.axvline(x=RELEVANCE_THRESHOLD, color='gray', linestyle='--', linewidth=1, label=f"Relevance Threshold: {RELEVANCE_THRESHOLD}")  

    # 调整 X 轴范围
    plt.xlim(min(df["relevance_score"]) - 0.05, max(df["relevance_score"]) + 0.05)  
    plt.ylim(min(df["sentiment_score"]) - 0.05, max(df["sentiment_score"]) + 0.05)  

    # 添加标题，包含加权情感分数
    plt.xlabel("Relevance Score", fontsize=12)
    plt.ylabel("Sentiment Score", fontsize=12)
    plt.title(f"{ticker} Sentiment Analysis\n Weighted Sentiment Score: {weighted_sentiment_score:.3f}", fontsize=14)
    plt.legend()

    # 保存图片
    img_path = f"static/{ticker}_sentiment_plot.png"
    plt.savefig(img_path, format='png', bbox_inches='tight')
    plt.close()

    return img_path

@app.route("/")
def home():
    return render_template("b_index.html")

@app.route("/get_news", methods=["POST"])
def get_news():
    ticker = request.form.get("ticker", "").upper()

    if not ticker:
        return jsonify({"error": "Stock ticker is required"}), 400

    # 获取新闻数据
    news_df = get_stock_news_sentiment(ticker, API_KEY)

    if news_df.empty:
        return jsonify({"error": "No news found"}), 404

    # 生成情感分析图
    img_path = generate_sentiment_plot(news_df, ticker)

    # 转换数据为 JSON
    news_json = news_df.to_dict(orient="records")
    
    return jsonify({"ticker": ticker, "news": news_json, "plot_url": img_path})

if __name__ == "__main__":
    app.run(debug=False, port=5001)

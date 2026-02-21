import pytz
from datetime import datetime, time

def is_taiwan_market_open(symbol: str) -> bool:
    """
    檢查台灣市場是否在營業時段內
    
    時段限制：
    - 台股 (TSMC, UMC, Creative): 09:00 - 13:30
    - 台銀金價 (Gold): 09:00 - 15:30
    - 其他: 24/7 (True)
    
    Args:
        symbol: 標代碼
    Returns:
        bool: 是否在營業時段
    """
    # 24/7 監控的指標
    global_indices = ['BTC', 'USDTWD', 'USDVND', 'IntlGold', 'NTDVND']
    if symbol in global_indices:
        return True
        
    # 取得台灣目前時間
    tpe_tz = pytz.timezone('Asia/Taipei')
    now = datetime.now(tpe_tz)
    
    # 週六週日休市
    if now.weekday() >= 5:
        return False
        
    current_time = now.time()
    
    # 依照標的分別判斷
    if symbol in ['TSMC', 'UMC', 'Creative']:
        # 台股交易時間 09:00 - 13:30 (加 5 分鐘緩衝)
        start = time(9, 0)
        end = time(13, 35)
        return start <= current_time <= end
        
    if symbol == 'Gold':
        # 台銀金價交易時間 09:00 - 15:30 (加 5 分鐘緩衝)
        start = time(9, 0)
        end = time(15, 35)
        return start <= current_time <= end
        
    return True # 預設開啟

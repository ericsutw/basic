#!/usr/bin/env python3
"""
Gold Price Visualizer Module
視覺化黃金價格趨勢
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import Button
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Literal


# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False


TimeRange = Literal['1W', '1M', '3M', '6M', '1Y', 'ALL']


class GoldPriceVisualizer:
    def __init__(self, data_dir: str = "data"):
        """
        初始化視覺化模組
        
        Args:
            data_dir: 資料目錄
        """
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "gold_prices.csv"
    
    def load_data(self, time_range: TimeRange = 'ALL') -> pd.DataFrame:
        """
        載入指定時間範圍的資料
        
        Args:
            time_range: 時間範圍 ('1W', '1M', '3M', '6M', '1Y', 'ALL')
        
        Returns:
            過濾後的資料
        """
        if not self.data_file.exists():
            print("錯誤：找不到資料檔案")
            return pd.DataFrame()
        
        df = pd.read_csv(self.data_file, encoding='utf-8-sig')
        if df.empty:
            print("警告：資料檔案是空的")
            return df
        
        df['date'] = pd.to_datetime(df['date'])
        
        # 根據時間範圍過濾
        if time_range != 'ALL':
            end_date = datetime.now()
            
            if time_range == '1W':
                start_date = end_date - timedelta(weeks=1)
            elif time_range == '1M':
                start_date = end_date - timedelta(days=30)
            elif time_range == '3M':
                start_date = end_date - timedelta(days=90)
            elif time_range == '6M':
                start_date = end_date - timedelta(days=180)
            elif time_range == '1Y':
                start_date = end_date - timedelta(days=365)
            else:
                start_date = df['date'].min()
            
            df = df[df['date'] >= start_date]
        
        return df.sort_values('date')

    def _filter_data_by_range(self, df: pd.DataFrame, time_range: TimeRange) -> pd.DataFrame:
        """
        根據時間範圍過濾資料 (記憶體內操作)
        """
        if time_range == 'ALL':
            return df
            
        end_date = df['date'].max() # 使用資料中的最後日期作為基準，或者用 datetime.now()
        # 為了跟 load_data 一致，使用 datetime.now() 或是資料最後一天比較好？
        # load_data 使用 datetime.now()。這裡保持一致。
        end_date = datetime.now() 
        
        start_date = df['date'].min()
        
        if time_range == '1W':
            start_date = end_date - timedelta(weeks=1)
        elif time_range == '1M':
            start_date = end_date - timedelta(days=30)
        elif time_range == '3M':
            start_date = end_date - timedelta(days=90)
        elif time_range == '6M':
            start_date = end_date - timedelta(days=180)
        elif time_range == '1Y':
            start_date = end_date - timedelta(days=365)
            
        return df[df['date'] >= start_date]
    
    def _add_annotations(self, ax, df: pd.DataFrame):
        """
        在圖表上新增最高價、最低價、最新價的標註
        """
        if df.empty:
            return

        # 針對賣出價 (Sell Price) 進行標註
        prices = df['sell_price']
        dates = df['date']
        
        # 找出關鍵點
        curr_idx = df.index[-1]
        max_idx = prices.idxmax()
        min_idx = prices.idxmin()
        
        points = [
            ('最新', curr_idx, 'blue', -20),
            ('最高', max_idx, 'red', 20),
            ('最低', min_idx, 'green', -20)
        ]
        
        # 避免重複標註 (例如最新價剛好是最高價)
        seen_indices = set()
        
        for label, idx, color, offset_y in points:
            if idx in seen_indices:
                continue
            seen_indices.add(idx)
            
            date = dates[idx]
            price = prices[idx]
            date_str = date.strftime('%Y/%m/%d')
            
            ax.annotate(f'{label}: {price:.0f}\n({date_str})',
                        xy=(date, price),
                        xytext=(0, offset_y),
                        textcoords='offset points',
                        ha='center', va='center',
                        color=color,
                        fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8, ec=color),
                        arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color=color))

    def plot_price_trend(self, time_range: TimeRange = '1M', 
                        save_path: Optional[str] = None,
                        show: bool = True) -> Optional[str]:
        """
        繪製價格趨勢圖
        
        Args:
            time_range: 時間範圍
            save_path: 儲存路徑（如果要儲存圖片）
            show: 是否顯示圖表
        
        Returns:
            儲存的檔案路徑（如果有儲存）
        """
        # 載入所有資料以便切換
        full_df = self.load_data('ALL')
        
        if full_df.empty:
            print("沒有資料可以顯示")
            return None
            
        # 根據初始設定過濾
        df = self._filter_data_by_range(full_df, time_range)
        
        if df.empty:
             # 如果選定範圍沒資料，fallback 到所有資料或提示
             print(f"注意：{time_range} 範圍內沒有資料，顯示所有資料")
             df = full_df
             time_range = 'ALL'

        # 建立圖表，預留底部空間給按鈕
        fig, ax = plt.subplots(figsize=(12, 7))
        plt.subplots_adjust(bottom=0.2)
        
        # 儲存線條物件以便更新
        lines = {}
        
        def draw_plot(current_df, current_range):
            ax.clear()
            
            # 繪製買入價和賣出價曲線
            l1, = ax.plot(current_df['date'], current_df['buy_price'], 
                    label='買入價', color='#2E7D32', linewidth=2, marker='o', markersize=4)
            l2, = ax.plot(current_df['date'], current_df['sell_price'], 
                    label='賣出價', color='#C62828', linewidth=2, marker='s', markersize=4)
            
            lines['buy'] = l1
            lines['sell'] = l2
            
            # 填充區域
            ax.fill_between(current_df['date'], current_df['buy_price'], current_df['sell_price'], 
                            alpha=0.2, color='gray', label='價差')
            
            # 設定標題和標籤
            time_range_names = {
                '1W': '一週',
                '1M': '一個月',
                '3M': '三個月',
                '6M': '六個月',
                '1Y': '一年',
                'ALL': '全部'
            }
            title = f'台灣銀行黃金存摺牌價趨勢 ({time_range_names.get(current_range, current_range)})'
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('日期', fontsize=12)
            ax.set_ylabel('價格 (新台幣/公克)', fontsize=12)
            
            # 格式化 x 軸日期
            if current_range in ['1W', '1M']:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(current_df)//10)))
            elif current_range in ['3M', '6M']:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator())
            
            # 旋轉標籤
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            
            # 加入網格
            ax.grid(True, alpha=0.3, linestyle='--')
            
            # 加入標註
            self._add_annotations(ax, current_df)
            
            # 圖例
            ax.legend(loc='best', fontsize=10, framealpha=0.9)
            
            # 強制更新
            fig.canvas.draw_idle()

        # 初始繪圖
        draw_plot(df, time_range)
        
        # 建立按鈕
        # 位置: [left, bottom, width, height]
        button_axes = []
        buttons = []
        labels = ['1W', '1M', '3M', '6M', '1Y', 'ALL']
        
        # 計算按鈕位置，置中
        btn_width = 0.08
        btn_height = 0.05
        spacing = 0.02
        total_width = len(labels) * btn_width + (len(labels) - 1) * spacing
        start_x = (1.0 - total_width) / 2
        
        # 為了防止 Garbage Collection 回收按鈕物件，需要將它們儲存起來
        self._buttons = buttons 
        
        for i, label in enumerate(labels):
            ax_btn = plt.axes([start_x + i * (btn_width + spacing), 0.05, btn_width, btn_height])
            button_axes.append(ax_btn)
            btn = Button(ax_btn, label, hovercolor='0.975')
            
            # 使用 closure 捕捉 label
            def make_callback(r):
                def callback(event):
                    new_df = self._filter_data_by_range(full_df, r)
                    if not new_df.empty:
                        draw_plot(new_df, r)
                    else:
                        print(f"範圍 {r} 無資料")
                return callback
                
            btn.on_clicked(make_callback(label))
            buttons.append(btn)
        
        # 儲存圖片 (如果需要)
        # 注意：儲存圖片通常只會存初始狀態，與互動功能無關
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"圖表已儲存至: {save_path}")
        
        # 顯示圖表
        if show:
            plt.show()
        else:
            plt.close()
        
        return save_path
    
    def get_statistics(self, time_range: TimeRange = 'ALL') -> dict:
        """
        取得統計資訊
        
        Args:
            time_range: 時間範圍
        
        Returns:
            統計資訊字典
        """
        df = self.load_data(time_range)
        
        if df.empty:
            return {
                'total_records': 0,
                'date_range': None,
                'buy_price': {},
                'sell_price': {},
                'spread': {}
            }
        
        # 計算價差
        df['spread'] = df['sell_price'] - df['buy_price']
        
        return {
            'total_records': len(df),
            'date_range': (df['date'].min(), df['date'].max()),
            'buy_price': {
                'current': df['buy_price'].iloc[-1],
                'min': df['buy_price'].min(),
                'max': df['buy_price'].max(),
                'avg': df['buy_price'].mean(),
                'change': df['buy_price'].iloc[-1] - df['buy_price'].iloc[0] if len(df) > 1 else 0,
                'change_pct': ((df['buy_price'].iloc[-1] - df['buy_price'].iloc[0]) / df['buy_price'].iloc[0] * 100) if len(df) > 1 else 0
            },
            'sell_price': {
                'current': df['sell_price'].iloc[-1],
                'min': df['sell_price'].min(),
                'max': df['sell_price'].max(),
                'avg': df['sell_price'].mean(),
                'change': df['sell_price'].iloc[-1] - df['sell_price'].iloc[0] if len(df) > 1 else 0,
                'change_pct': ((df['sell_price'].iloc[-1] - df['sell_price'].iloc[0]) / df['sell_price'].iloc[0] * 100) if len(df) > 1 else 0
            },
            'spread': {
                'current': df['spread'].iloc[-1],
                'min': df['spread'].min(),
                'max': df['spread'].max(),
                'avg': df['spread'].mean()
            }
        }
    
    def print_statistics(self, time_range: TimeRange = 'ALL'):
        """
        列印統計資訊
        
        Args:
            time_range: 時間範圍
        """
        stats = self.get_statistics(time_range)
        
        if stats['total_records'] == 0:
            print("沒有資料")
            return
        
        time_range_names = {
            '1W': '一週',
            '1M': '一個月',
            '3M': '三個月',
            '6M': '六個月',
            '1Y': '一年',
            'ALL': '全部'
        }
        
        print(f"\n{'='*60}")
        print(f"黃金價格統計資訊 ({time_range_names[time_range]})")
        print(f"{'='*60}")
        print(f"資料筆數: {stats['total_records']}")
        print(f"日期範圍: {stats['date_range'][0].date()} 到 {stats['date_range'][1].date()}")
        
        print(f"\n【買入價】")
        print(f"  目前價格: {stats['buy_price']['current']:.2f} 元/公克")
        print(f"  最低價格: {stats['buy_price']['min']:.2f} 元/公克")
        print(f"  最高價格: {stats['buy_price']['max']:.2f} 元/公克")
        print(f"  平均價格: {stats['buy_price']['avg']:.2f} 元/公克")
        print(f"  價格變化: {stats['buy_price']['change']:+.2f} 元 ({stats['buy_price']['change_pct']:+.2f}%)")
        
        print(f"\n【賣出價】")
        print(f"  目前價格: {stats['sell_price']['current']:.2f} 元/公克")
        print(f"  最低價格: {stats['sell_price']['min']:.2f} 元/公克")
        print(f"  最高價格: {stats['sell_price']['max']:.2f} 元/公克")
        print(f"  平均價格: {stats['sell_price']['avg']:.2f} 元/公克")
        print(f"  價格變化: {stats['sell_price']['change']:+.2f} 元 ({stats['sell_price']['change_pct']:+.2f}%)")
        
        print(f"\n【買賣價差】")
        print(f"  目前價差: {stats['spread']['current']:.2f} 元/公克")
        print(f"  最小價差: {stats['spread']['min']:.2f} 元/公克")
        print(f"  最大價差: {stats['spread']['max']:.2f} 元/公克")
        print(f"  平均價差: {stats['spread']['avg']:.2f} 元/公克")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    # 測試程式碼
    visualizer = GoldPriceVisualizer()
    
    # 顯示統計資訊
    visualizer.print_statistics('1M')
    
    # 繪製圖表
    print("繪製一個月趨勢圖...")
    visualizer.plot_price_trend('1M', show=False, save_path='data/gold_price_1m.png')

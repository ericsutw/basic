import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import Button
from datetime import datetime, timedelta
from typing import Optional, Literal

# 設定中文字體
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

TimeRange = Literal['1W', '1M', '3M', '6M', '1Y', 'ALL']

class CurrencyVisualizer:
    def __init__(self, storage):
        self.storage = storage

    def _filter_data(self, df: pd.DataFrame, time_range: TimeRange) -> pd.DataFrame:
        if time_range == 'ALL':
            return df
            
        end_date = df['Date'].max()
        start_date = df['Date'].min()
        
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
            
        return df[df['Date'] >= start_date]

    def _add_annotations(self, ax, df: pd.DataFrame, price_col='Close'):
        if df.empty:
            return

        prices = df[price_col]
        dates = df['Date']
        
        curr_idx = df.index[-1]
        max_idx = prices.idxmax()
        min_idx = prices.idxmin()
        
        points = [
            ('最新', curr_idx, 'blue', -20),
            ('最高', max_idx, 'red', 20),
            ('最低', min_idx, 'green', -20)
        ]
        
        seen_indices = set()
        
        for label, idx, color, offset_y in points:
            if idx in seen_indices:
                continue
            seen_indices.add(idx)
            
            # DEBUG
            # print(f"DEBUG: Processing idx={idx}")
            
            # Define variables first
            try:
                date = dates[idx]
                price = float(prices[idx])
                date_str = date.strftime('%Y/%m/%d')
            except Exception as e:
                print(f"Error accessing data for idx {idx}: {e}")
                continue

            # Convert pandas Timestamp to python datetime
            if isinstance(date, pd.Timestamp):
                date = date.to_pydatetime()
            
            try:
                ax.annotate(f'{label}: {price:,.2f}\n({date_str})',
                            xy=(date, price),
                            xytext=(0, offset_y),
                            textcoords='offset points',
                            ha='center', va='center',
                            color=color,
                            fontweight='bold',
                            bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.8, ec=color),
                            arrowprops=dict(arrowstyle='->', color=color))
            except Exception as e:
                print(f"Error adding annotation {label}: {e}")
                import traceback
                traceback.print_exc()

    def plot_trend(self, symbol: str, title: str, 
                  time_range: TimeRange = '1M', 
                  save_path: Optional[str] = None,
                  show: bool = True):
        
        full_df = self.storage.load_data(symbol)
        
        if full_df.empty:
            print(f"沒有 {symbol} 的資料")
            return

        # 預設過濾
        df = self._filter_data(full_df, time_range)
        if df.empty:
            df = full_df
            time_range = 'ALL'

        fig, ax = plt.subplots(figsize=(12, 7))
        plt.subplots_adjust(bottom=0.2)
        
        def draw_plot(current_df, current_range):
            ax.clear()
            
            price_col = 'Close'
            ax.plot(current_df['Date'], current_df[price_col], 
                   label=symbol, color='#1976D2', linewidth=2)
            
            ax.fill_between(current_df['Date'], current_df[price_col], 
                            alpha=0.1, color='#1976D2')
            
            ax.set_title(f'{title} 匯率趨勢 ({current_range})', fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('日期', fontsize=12)
            ax.set_ylabel('價格', fontsize=12)
            
            # Format X axis
            if current_range in ['1W', '1M']:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y/%m'))
                
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            ax.grid(True, alpha=0.3, linestyle='--')
            
            self._add_annotations(ax, current_df, price_col)
            
            ax.legend(loc='best')
            fig.canvas.draw_idle()

        draw_plot(df, time_range)
        
        # Buttons
        button_axes = []
        buttons = []
        labels = ['1W', '1M', '3M', '6M', '1Y', 'ALL']
        
        btn_width = 0.08
        btn_height = 0.05
        spacing = 0.02
        total_width = len(labels) * btn_width + (len(labels) - 1) * spacing
        start_x = (1.0 - total_width) / 2
        
        self._buttons = buttons # Keep reference
        
        for i, label in enumerate(labels):
            ax_btn = plt.axes([start_x + i * (btn_width + spacing), 0.05, btn_width, btn_height])
            button_axes.append(ax_btn)
            btn = Button(ax_btn, label, hovercolor='0.975')
            
            def make_callback(r):
                def callback(event):
                    new_df = self._filter_data(full_df, r)
                    if not new_df.empty:
                        draw_plot(new_df, r)
                return callback
                
            btn.on_clicked(make_callback(label))
            buttons.append(btn)
            
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"圖表已儲存至: {save_path}")
            
        if show:
            plt.show()
        else:
            plt.close()

#!/usr/bin/env python3
"""
System Monitor Dashboard
即時監控系統資源使用情況，顯示使用最多資源的程式
支援互動式切換不同資源視圖
"""

import psutil
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
import argparse
from pynput import keyboard
import threading


class SystemMonitor:
    def __init__(self, top_n=10, refresh_rate=1.0):
        """
        初始化系統監控器
        
        Args:
            top_n: 顯示前 N 個程式
            refresh_rate: 更新頻率（秒）
        """
        self.top_n = top_n
        self.refresh_rate = refresh_rate
        self.console = Console()
        
        # 視圖模式: 'cpu', 'memory', 'disk', 'network', 'uptime'
        self.view_mode = 'cpu'
        self.view_lock = threading.Lock()
        self.running = True
        
        # 用於計算 I/O 速率
        self.last_disk_io = psutil.disk_io_counters()
        self.last_net_io = psutil.net_io_counters()
        self.last_time = time.time()
        
        # 用於計算程式級別的 I/O 速率
        self.last_process_io = {}
        
    def format_bytes(self, bytes_value):
        """格式化位元組為人類可讀格式"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f}PB"
    
    def format_uptime(self, seconds):
        """格式化存活時間為人類可讀格式"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if days > 0:
            return f"{days}天 {hours}時"
        elif hours > 0:
            return f"{hours}時 {minutes}分"
        elif minutes > 0:
            return f"{minutes}分 {secs}秒"
        else:
            return f"{secs}秒"
    
    def get_process_info(self):
        """獲取所有程式的資訊"""
        processes = []
        current_time = time.time()
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'io_counters', 'create_time']):
            try:
                pinfo = proc.info
                pid = pinfo['pid']
                
                # 獲取 I/O 資訊
                io_counters = pinfo.get('io_counters')
                if io_counters:
                    read_bytes = io_counters.read_bytes
                    write_bytes = io_counters.write_bytes
                    
                    # 計算 I/O 速率
                    if pid in self.last_process_io:
                        last_read, last_write, last_time = self.last_process_io[pid]
                        time_delta = current_time - last_time
                        if time_delta > 0:
                            read_speed = (read_bytes - last_read) / time_delta
                            write_speed = (write_bytes - last_write) / time_delta
                        else:
                            read_speed = 0
                            write_speed = 0
                    else:
                        read_speed = 0
                        write_speed = 0
                    
                    # 更新記錄
                    self.last_process_io[pid] = (read_bytes, write_bytes, current_time)
                else:
                    read_bytes = 0
                    write_bytes = 0
                    read_speed = 0
                    write_speed = 0
                
                # 計算存活時間
                create_time = pinfo.get('create_time', 0)
                uptime = current_time - create_time if create_time else 0
                
                processes.append({
                    'pid': pid,
                    'name': pinfo['name'],
                    'cpu': pinfo['cpu_percent'] or 0,
                    'memory': pinfo['memory_info'].rss if pinfo['memory_info'] else 0,
                    'read_bytes': read_bytes,
                    'write_bytes': write_bytes,
                    'read_speed': read_speed,
                    'write_speed': write_speed,
                    'disk_total': read_speed + write_speed,
                    'uptime': uptime,
                    'create_time': create_time,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # 清理已不存在的程式記錄
        current_pids = {p['pid'] for p in processes}
        self.last_process_io = {pid: data for pid, data in self.last_process_io.items() if pid in current_pids}
        
        return processes
    
    def get_system_io_stats(self):
        """獲取系統 I/O 統計"""
        current_time = time.time()
        time_delta = current_time - self.last_time
        
        # 磁碟 I/O
        current_disk_io = psutil.disk_io_counters()
        if current_disk_io and self.last_disk_io:
            disk_read_speed = (current_disk_io.read_bytes - self.last_disk_io.read_bytes) / time_delta
            disk_write_speed = (current_disk_io.write_bytes - self.last_disk_io.write_bytes) / time_delta
        else:
            disk_read_speed = 0
            disk_write_speed = 0
        
        # 網路 I/O
        current_net_io = psutil.net_io_counters()
        if current_net_io and self.last_net_io:
            net_sent_speed = (current_net_io.bytes_sent - self.last_net_io.bytes_sent) / time_delta
            net_recv_speed = (current_net_io.bytes_recv - self.last_net_io.bytes_recv) / time_delta
        else:
            net_sent_speed = 0
            net_recv_speed = 0
        
        # 更新上次的值
        self.last_disk_io = current_disk_io
        self.last_net_io = current_net_io
        self.last_time = current_time
        
        return {
            'disk_read': disk_read_speed,
            'disk_write': disk_write_speed,
            'net_sent': net_sent_speed,
            'net_recv': net_recv_speed,
        }
    
    def create_system_overview(self, io_stats):
        """建立系統概覽面板"""
        cpu_percent = psutil.cpu_percent(interval=0)
        memory = psutil.virtual_memory()
        
        overview = Table.grid(padding=(0, 2))
        overview.add_column(style="cyan", justify="right")
        overview.add_column(style="white")
        
        overview.add_row("CPU:", f"{cpu_percent:.1f}%")
        overview.add_row("記憶體:", f"{memory.percent:.1f}% ({self.format_bytes(memory.used)}/{self.format_bytes(memory.total)})")
        overview.add_row("磁碟讀取:", f"{self.format_bytes(io_stats['disk_read'])}/s")
        overview.add_row("磁碟寫入:", f"{self.format_bytes(io_stats['disk_write'])}/s")
        overview.add_row("網路上傳:", f"{self.format_bytes(io_stats['net_sent'])}/s")
        overview.add_row("網路下載:", f"{self.format_bytes(io_stats['net_recv'])}/s")
        
        return Panel(overview, title="[bold cyan]系統概覽[/bold cyan]", border_style="cyan")
    
    def create_process_table_by_view(self, processes):
        """根據當前視圖模式建立程式列表表格"""
        with self.view_lock:
            current_view = self.view_mode
        
        # 視圖配置
        view_configs = {
            'cpu': {
                'title': '[bold green]CPU 使用率 Top {}[/bold green]',
                'sort_key': 'cpu',
                'columns': [
                    ('PID', 'dim', 8),
                    ('程式名稱', 'cyan', 35),
                    ('CPU %', 'green', 'right'),
                    ('記憶體', 'yellow', 'right'),
                ],
                'data_func': lambda p: [
                    str(p['pid']),
                    p['name'][:33] if len(p['name']) > 33 else p['name'],
                    f"{p['cpu']:.1f}",
                    self.format_bytes(p['memory']),
                ]
            },
            'memory': {
                'title': '[bold yellow]記憶體使用 Top {}[/bold yellow]',
                'sort_key': 'memory',
                'columns': [
                    ('PID', 'dim', 8),
                    ('程式名稱', 'cyan', 35),
                    ('記憶體', 'yellow', 'right'),
                    ('CPU %', 'green', 'right'),
                ],
                'data_func': lambda p: [
                    str(p['pid']),
                    p['name'][:33] if len(p['name']) > 33 else p['name'],
                    self.format_bytes(p['memory']),
                    f"{p['cpu']:.1f}",
                ]
            },
            'disk': {
                'title': '[bold blue]磁碟 I/O Top {}[/bold blue]',
                'sort_key': 'disk_total',
                'columns': [
                    ('PID', 'dim', 8),
                    ('程式名稱', 'cyan', 25),
                    ('讀取速度', 'blue', 'right'),
                    ('寫入速度', 'blue', 'right'),
                    ('總計', 'magenta', 'right'),
                ],
                'data_func': lambda p: [
                    str(p['pid']),
                    p['name'][:23] if len(p['name']) > 23 else p['name'],
                    f"{self.format_bytes(p['read_speed'])}/s",
                    f"{self.format_bytes(p['write_speed'])}/s",
                    f"{self.format_bytes(p['disk_total'])}/s",
                ]
            },
            'network': {
                'title': '[bold magenta]網路 I/O Top {}[/bold magenta]',
                'sort_key': 'disk_total',  # 暫時使用 disk_total，實際應該追蹤網路
                'columns': [
                    ('PID', 'dim', 8),
                    ('程式名稱', 'cyan', 35),
                    ('I/O 活動', 'magenta', 'right'),
                    ('CPU %', 'green', 'right'),
                ],
                'data_func': lambda p: [
                    str(p['pid']),
                    p['name'][:33] if len(p['name']) > 33 else p['name'],
                    f"{self.format_bytes(p['disk_total'])}/s",
                    f"{p['cpu']:.1f}",
                ]
            },
            'uptime': {
                'title': '[bold cyan]程式存活時間 Top {}[/bold cyan]',
                'sort_key': 'uptime',
                'columns': [
                    ('PID', 'dim', 8),
                    ('程式名稱', 'cyan', 30),
                    ('存活時間', 'green', 'right'),
                    ('啟動時間', 'yellow', 20),
                    ('記憶體', 'magenta', 'right'),
                ],
                'data_func': lambda p: [
                    str(p['pid']),
                    p['name'][:28] if len(p['name']) > 28 else p['name'],
                    self.format_uptime(p['uptime']),
                    datetime.fromtimestamp(p['create_time']).strftime('%m-%d %H:%M') if p['create_time'] else 'N/A',
                    self.format_bytes(p['memory']),
                ]
            },
        }
        
        config = view_configs[current_view]
        table = Table(
            title=config['title'].format(self.top_n),
            show_header=True,
            header_style="bold white",
            expand=True
        )
        
        # 添加列
        for col_name, col_style, *col_width in config['columns']:
            if col_width and isinstance(col_width[0], int):
                table.add_column(col_name, style=col_style, width=col_width[0])
            elif col_width and col_width[0] == 'right':
                table.add_column(col_name, style=col_style, justify='right')
            else:
                table.add_column(col_name, style=col_style)
        
        # 排序並取前 N 個
        sorted_processes = sorted(processes, key=lambda x: x[config['sort_key']], reverse=True)[:self.top_n]
        
        # 添加資料
        for proc in sorted_processes:
            table.add_row(*config['data_func'](proc))
        
        return table
    
    def create_help_panel(self):
        """建立快捷鍵說明面板"""
        with self.view_lock:
            current_view = self.view_mode
        
        view_names = {
            'cpu': 'CPU 使用率',
            'memory': '記憶體使用',
            'disk': '磁碟 I/O',
            'network': '網路 I/O',
            'uptime': '程式存活時間'
        }
        
        help_text = Text()
        help_text.append("當前視圖: ", style="bold white")
        help_text.append(f"{view_names[current_view]}", style="bold yellow")
        help_text.append("  |  ", style="dim")
        help_text.append("快捷鍵: ", style="bold white")
        help_text.append("[1/C]", style="green")
        help_text.append(" CPU  ", style="white")
        help_text.append("[2/M]", style="yellow")
        help_text.append(" 記憶體  ", style="white")
        help_text.append("[3/D]", style="blue")
        help_text.append(" 磁碟  ", style="white")
        help_text.append("[4/N]", style="magenta")
        help_text.append(" 網路  ", style="white")
        help_text.append("[5/U]", style="cyan")
        help_text.append(" 存活時間  ", style="white")
        help_text.append("[Q]", style="red")
        help_text.append(" 退出", style="white")
        
        return Panel(help_text, border_style="dim")
    
    def generate_display(self):
        """生成顯示內容"""
        processes = self.get_process_info()
        io_stats = self.get_system_io_stats()
        
        # 建立佈局
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="overview", size=10),
            Layout(name="table"),
            Layout(name="help", size=3)
        )
        
        # 標題
        header_text = Text(f"系統監控面板 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                          style="bold white on blue", justify="center")
        layout["header"].update(Panel(header_text))
        
        # 系統概覽
        layout["overview"].update(self.create_system_overview(io_stats))
        
        # 程式表格
        layout["table"].update(self.create_process_table_by_view(processes))
        
        # 快捷鍵說明
        layout["help"].update(self.create_help_panel())
        
        return layout
    
    def on_press(self, key):
        """鍵盤按鍵處理"""
        try:
            if hasattr(key, 'char') and key.char:
                char = key.char.lower()
                with self.view_lock:
                    if char == '1' or char == 'c':
                        self.view_mode = 'cpu'
                    elif char == '2' or char == 'm':
                        self.view_mode = 'memory'
                    elif char == '3' or char == 'd':
                        self.view_mode = 'disk'
                    elif char == '4' or char == 'n':
                        self.view_mode = 'network'
                    elif char == '5' or char == 'u':
                        self.view_mode = 'uptime'
                    elif char == 'q':
                        self.running = False
                        return False  # 停止監聽
        except AttributeError:
            pass
    
    def run(self):
        """執行監控"""
        # 啟動鍵盤監聽器
        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
        
        try:
            with Live(self.generate_display(), refresh_per_second=1/self.refresh_rate, console=self.console) as live:
                while self.running:
                    time.sleep(self.refresh_rate)
                    live.update(self.generate_display())
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            listener.stop()
            self.console.print("\n[bold red]監控已停止[/bold red]")


def main():
    parser = argparse.ArgumentParser(description='系統監控面板 - 即時顯示系統資源使用情況')
    parser.add_argument('-n', '--top', type=int, default=10, help='顯示前 N 個程式 (預設: 10)')
    parser.add_argument('-r', '--refresh', type=float, default=1.0, help='更新頻率（秒）(預設: 1.0)')
    
    args = parser.parse_args()
    
    monitor = SystemMonitor(top_n=args.top, refresh_rate=args.refresh)
    monitor.run()


if __name__ == '__main__':
    main()

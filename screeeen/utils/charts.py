import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
from typing import Dict, List, Optional
from loguru import logger
import io
from datetime import datetime

class ChartGenerator:
    """Генерация графиков для криптовалют"""
    
    @staticmethod
    def generate_candlestick_chart(
        df: pd.DataFrame,
        symbol: str,
        signals: List[Dict] = None,
        levels: Dict = None,
        save_path: str = None
    ) -> Optional[io.BytesIO]:
        """
        Генерировать candlestick график с разметкой
        
        Args:
            df: DataFrame с OHLCV данными
            symbol: Название пары
            signals: Список сигналов для отображения
            levels: Словарь с уровнями поддержки/сопротивления
            save_path: Путь для сохранения (опционально)
        
        Returns:
            BytesIO объект с изображением графика
        """
        try:
            # Подготовка данных
            plot_df = df.copy()
            plot_df.index = pd.to_datetime(plot_df.index)
            
            # Настройка стиля
            mc = mpf.make_marketcolors(
                up='#26a69a',
                down='#ef5350',
                edge='inherit',
                wick='inherit',
                volume='in',
                alpha=0.9
            )
            
            style = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle=':',
                y_on_right=True,
                figcolor='#1e1e1e',
                facecolor='#1e1e1e',
                edgecolor='#4a4a4a',
                gridcolor='#2a2a2a'
            )
            
            # Добавление индикаторов
            add_plots = []
            
            # Moving Averages
            if 'ema_9' in plot_df.columns and 'ema_21' in plot_df.columns:
                add_plots.extend([
                    mpf.make_addplot(plot_df['ema_9'], color='#2196F3', width=1.5),
                    mpf.make_addplot(plot_df['ema_21'], color='#FF9800', width=1.5)
                ])
            
            # Bollinger Bands
            if all(col in plot_df.columns for col in ['bb_upper', 'bb_middle', 'bb_lower']):
                add_plots.extend([
                    mpf.make_addplot(plot_df['bb_upper'], color='#9C27B0', width=0.7, linestyle='--'),
                    mpf.make_addplot(plot_df['bb_middle'], color='#9C27B0', width=0.7),
                    mpf.make_addplot(plot_df['bb_lower'], color='#9C27B0', width=0.7, linestyle='--')
                ])
            
            # Horizontal lines для уровней
            hlines = {}
            if levels:
                if levels.get('support'):
                    for level in levels['support'][:3]:
                        hlines[level] = dict(color='#4CAF50', linestyle='--', linewidth=1.5)
                
                if levels.get('resistance'):
                    for level in levels['resistance'][:3]:
                        hlines[level] = dict(color='#F44336', linestyle='--', linewidth=1.5)
            
            # Создание графика
            fig, axes = mpf.plot(
                plot_df,
                type='candle',
                style=style,
                title=f'\n{symbol} - {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                ylabel='Price (USD)',
                ylabel_lower='Volume',
                volume=True,
                addplot=add_plots if add_plots else None,
                hlines=hlines if hlines else None,
                figsize=(14, 8),
                panel_ratios=(3, 1),
                returnfig=True,
                warn_too_much_data=len(plot_df) + 1
            )
            
            # Сохранение в BytesIO
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1e1e1e')
            buf.seek(0)
            plt.close(fig)
            
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(buf.getvalue())
                buf.seek(0)
            
            return buf
            
        except Exception as e:
            logger.error(f"Ошибка генерации графика: {e}")
            return None
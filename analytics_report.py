#!/usr/bin/env python3
"""
Analytics Report Generator for YouTube Summarizer Bot
Generates reports and charts from user activity logs
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns
from typing import List, Dict

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from analytics.logger import UserActivityLogger


class AnalyticsReporter:
    """Генератор аналитических отчетов"""
    
    def __init__(self, db_path: str = "data/analytics.db"):
        self.logger = UserActivityLogger(db_path)
        # Настройка стилей графиков
        plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
        sns.set_palette("husl")
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
    
    def generate_command_stats_chart(self, days: int = 30, save_path: str = None):
        """Генерация графика статистики по командам"""
        stats = self.logger.get_command_stats(days)
        
        if not stats:
            print("Нет данных для генерации графика команд")
            return
        
        # Подготовка данных
        commands = [stat.command for stat in stats]
        uses = [stat.total_uses for stat in stats]
        users = [stat.unique_users for stat in stats]
        
        # Создание графика
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # График использования команд
        ax1.bar(commands, uses, color='skyblue', alpha=0.7)
        ax1.set_title(f'Использование команд за {days} дней')
        ax1.set_xlabel('Команды')
        ax1.set_ylabel('Количество использований')
        ax1.tick_params(axis='x', rotation=45)
        
        # График уникальных пользователей
        ax2.bar(commands, users, color='lightcoral', alpha=0.7)
        ax2.set_title(f'Уникальные пользователи по командам за {days} дней')
        ax2.set_xlabel('Команды')
        ax2.set_ylabel('Уникальные пользователи')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def generate_daily_activity_chart(self, days: int = 30, save_path: str = None):
        """Генерация графика ежедневной активности"""
        daily_stats = self.logger.get_daily_activity(days)
        
        if not daily_stats:
            print("Нет данных для генерации графика ежедневной активности")
            return
        
        # Подготовка данных
        dates = [datetime.fromisoformat(stat['date']) for stat in daily_stats]
        activities = [stat['total_activities'] for stat in daily_stats]
        users = [stat['unique_users'] for stat in daily_stats]
        summarize_requests = [stat['summarize_requests'] for stat in daily_stats]
        
        # Создание графика
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # График общей активности
        ax1.plot(dates, activities, marker='o', linewidth=2, label='Всего активности')
        ax1.plot(dates, users, marker='s', linewidth=2, label='Уникальные пользователи')
        ax1.plot(dates, summarize_requests, marker='^', linewidth=2, label='Запросы обобщения')
        ax1.set_title(f'Ежедневная активность за {days} дней')
        ax1.set_ylabel('Количество')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Форматирование дат
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days//10)))
        
        # График коэффициента использования
        if activities:
            usage_rate = [req/act*100 if act > 0 else 0 for req, act in zip(summarize_requests, activities)]
            ax2.bar(dates, usage_rate, alpha=0.7, color='orange')
            ax2.set_title('Коэффициент использования основной функции (%)')
            ax2.set_xlabel('Дата')
            ax2.set_ylabel('Процент запросов обобщения')
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax2.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days//10)))
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def generate_user_activity_chart(self, days: int = 30, top_users: int = 10, save_path: str = None):
        """Генерация графика активности пользователей"""
        users = self.logger.get_active_users(days)
        
        if not users:
            print("Нет данных для генерации графика активности пользователей")
            return
        
        # Берем топ пользователей
        top_users_data = users[:top_users]
        
        # Подготовка данных
        user_labels = []
        activities = []
        commands_used = []
        
        for user in top_users_data:
            username = user['username'] or f"user_{user['user_id']}"
            if user['first_name']:
                username = f"{user['first_name']} (@{username})" if user['username'] else user['first_name']
            user_labels.append(username)
            activities.append(user['activity_count'])
            commands_used.append(user['commands_used'])
        
        # Создание графика
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # График активности
        bars1 = ax1.barh(user_labels, activities, color='lightgreen', alpha=0.7)
        ax1.set_title(f'Топ {top_users} самых активных пользователей за {days} дней')
        ax1.set_xlabel('Количество действий')
        
        # Добавляем значения на бары
        for i, bar in enumerate(bars1):
            width = bar.get_width()
            ax1.text(width + max(activities)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{int(width)}', ha='left', va='center')
        
        # График разнообразия команд
        bars2 = ax2.barh(user_labels, commands_used, color='lightblue', alpha=0.7)
        ax2.set_title(f'Разнообразие используемых команд')
        ax2.set_xlabel('Количество разных команд')
        
        # Добавляем значения на бары
        for i, bar in enumerate(bars2):
            width = bar.get_width()
            ax2.text(width + max(commands_used)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{int(width)}', ha='left', va='center')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def generate_video_popularity_chart(self, days: int = 30, top_videos: int = 15, save_path: str = None):
        """Генерация графика популярности видео"""
        videos = self.logger.get_popular_videos(days)
        
        if not videos:
            print("Нет данных для генерации графика популярности видео")
            return
        
        # Берем топ видео
        top_videos_data = videos[:top_videos]
        
        # Подготовка данных
        video_titles = []
        processing_counts = []
        unique_users = []
        
        for video in top_videos_data:
            # Сокращаем длинные названия
            title = video['title'][:50] + '...' if len(video['title']) > 50 else video['title']
            video_titles.append(title)
            processing_counts.append(video['processing_count'])
            unique_users.append(video['unique_users'])
        
        # Создание графика
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # График популярности
        bars = ax.barh(video_titles, processing_counts, color='gold', alpha=0.7)
        ax.set_title(f'Топ {top_videos} самых популярных видео за {days} дней')
        ax.set_xlabel('Количество обработок')
        
        # Добавляем значения на бары
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + max(processing_counts)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{int(width)} ({unique_users[i]} польз.)', ha='left', va='center', fontsize=8)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def print_summary_report(self, days: int = 30):
        """Печать краткого отчета"""
        print(f"\n{'='*60}")
        print(f"ОТЧЕТ ПО АКТИВНОСТИ БОТА ЗА {days} ДНЕЙ")
        print(f"{'='*60}")
        
        # Статистика команд
        print(f"\n📊 СТАТИСТИКА КОМАНД:")
        print("-" * 40)
        command_stats = self.logger.get_command_stats(days)
        
        if command_stats:
            total_commands = sum(stat.total_uses for stat in command_stats)
            total_unique_users = len(set(self.logger.get_active_users(days)))
            
            print(f"Всего команд выполнено: {total_commands}")
            print(f"Уникальных пользователей: {total_unique_users}")
            print(f"Среднее команд на пользователя: {total_commands/total_unique_users:.1f}")
            print()
            
            for stat in command_stats:
                print(f"/{stat.command:<15} - {stat.total_uses:>3} исп. | {stat.unique_users:>2} польз. | "
                      f"{stat.success_rate*100:>5.1f}% успех")
        
        # Топ пользователи
        print(f"\n👥 ТОП-5 АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ:")
        print("-" * 40)
        active_users = self.logger.get_active_users(days)
        
        for i, user in enumerate(active_users[:5], 1):
            username = user['username'] or f"user_{user['user_id']}"
            name = user['first_name'] or username
            print(f"{i}. {name:<20} - {user['activity_count']:>3} действий | "
                  f"{user['commands_used']} команд")
        
        # Популярные видео
        print(f"\n🎥 ТОП-5 ПОПУЛЯРНЫХ ВИДЕО:")
        print("-" * 40)
        popular_videos = self.logger.get_popular_videos(days)
        
        for i, video in enumerate(popular_videos[:5], 1):
            title = video['title'][:40] + '...' if len(video['title']) > 40 else video['title']
            print(f"{i}. {title:<43} - {video['processing_count']} обр.")
        
        print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Генератор аналитических отчетов для YouTube Summarizer Bot')
    parser.add_argument('--days', type=int, default=30, help='Количество дней для анализа (по умолчанию: 30)')
    parser.add_argument('--db-path', type=str, default='data/analytics.db', help='Путь к базе данных')
    parser.add_argument('--save-charts', type=str, help='Путь для сохранения графиков (без расширения)')
    parser.add_argument('--report-only', action='store_true', help='Только текстовый отчет, без графиков')
    
    args = parser.parse_args()
    
    # Проверяем существование базы данных
    if not Path(args.db_path).exists():
        print(f"❌ База данных не найдена: {args.db_path}")
        print("Убедитесь, что бот работал и генерировал логи.")
        sys.exit(1)
    
    reporter = AnalyticsReporter(args.db_path)
    
    # Генерируем текстовый отчет
    reporter.print_summary_report(args.days)
    
    if not args.report_only:
        print(f"\n📈 Генерируем графики...")
        
        # Определяем пути для сохранения
        save_commands = f"{args.save_charts}_commands.png" if args.save_charts else None
        save_daily = f"{args.save_charts}_daily.png" if args.save_charts else None
        save_users = f"{args.save_charts}_users.png" if args.save_charts else None
        save_videos = f"{args.save_charts}_videos.png" if args.save_charts else None
        
        # Генерируем графики
        try:
            reporter.generate_command_stats_chart(args.days, save_commands)
            reporter.generate_daily_activity_chart(args.days, save_daily)
            reporter.generate_user_activity_chart(args.days, save_path=save_users)
            reporter.generate_video_popularity_chart(args.days, save_path=save_videos)
            
            if args.save_charts:
                print(f"✅ Графики сохранены с префиксом: {args.save_charts}")
        
        except ImportError as e:
            print(f"❌ Ошибка импорта для генерации графиков: {e}")
            print("Установите необходимые библиотеки: pip install matplotlib seaborn pandas")
        except Exception as e:
            print(f"❌ Ошибка при генерации графиков: {e}")


if __name__ == "__main__":
    main() 
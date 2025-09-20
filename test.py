import aiohttp
import asyncio
import ssl
import time
from datetime import datetime
from urllib.parse import urlparse
import json
import logging
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import base64
import certifi

# Настройка logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AsyncWebsiteChecker:
    def __init__(self, timeout: int = 10, max_concurrent: int = 10, verify_ssl: bool = False):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_concurrent = max_concurrent
        self.verify_ssl = verify_ssl
        
        # Создаем кастомный SSL контекст
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        if not verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
    
    async def check_website(self, session: aiohttp.ClientSession, url: str) -> Dict:
        """Асинхронная проверка сайта"""
        results = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'response_time_ms': None,
            'status_code': None,
            'content_available': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            
            # Используем наш SSL контекст
            async with session.get(
                url, 
                timeout=self.timeout, 
                ssl=self.ssl_context if self.verify_ssl else False
            ) as response:
                end_time = time.time()
                
                results['response_time_ms'] = round((end_time - start_time) * 1000, 2)
                results['status_code'] = response.status
                results['status'] = 'up' if response.status == 200 else 'down'
                
                # Проверка контента
                content = await response.text()
                results['content_available'] = self.check_content_availability(content, response.status)
                
                logger.info(f"✓ {url} - {response.status} ({results['response_time_ms']}ms)")
                
        except aiohttp.ClientSSLError as e:
            # Пробуем без SSL проверки
            if self.verify_ssl:
                logger.warning(f"SSL error for {url}, retrying without verification...")
                return await self.check_website_without_ssl(session, url)
            else:
                results['status'] = 'ssl_error'
                results['error'] = str(e)
                logger.error(f"SSL error for {url}: {e}")
                
        except aiohttp.ClientError as e:
            results['status'] = 'down'
            results['error'] = str(e)
            logger.error(f"Connection error for {url}: {e}")
            
        except asyncio.TimeoutError:
            results['status'] = 'timeout'
            results['error'] = 'Request timeout'
            logger.warning(f"Timeout for {url}")
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Unexpected error for {url}: {e}")
        
        return results
    
    async def check_website_without_ssl(self, session: aiohttp.ClientSession, url: str) -> Dict:
        """Проверка сайта без SSL верификации"""
        connector = aiohttp.TCPConnector(ssl=False)
        results = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'response_time_ms': None,
            'status_code': None,
            'content_available': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            async with session.get(url, timeout=self.timeout, connector=connector) as response:
                end_time = time.time()
                
                results['response_time_ms'] = round((end_time - start_time) * 1000, 2)
                results['status_code'] = response.status
                results['status'] = 'up' if response.status == 200 else 'down'
                
                content = await response.text()
                results['content_available'] = self.check_content_availability(content, response.status)
                
                logger.info(f"✓ {url} - {response.status} ({results['response_time_ms']}ms) [No SSL]")
                
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            logger.error(f"Error for {url} without SSL: {e}")
        
        return results
    
    def check_content_availability(self, content: str, status_code: int) -> bool:
        """Проверка доступности контента"""
        if status_code != 200:
            return False
            
        content = content.strip()
        return len(content) > 50 and not any(
            error in content.lower() for error in [
                'error', 'not found', '502', '503', '504', '500', '404', '403'
            ]
        )
    
    async def check_multiple_websites(self, urls: List[str]) -> List[Dict]:
        """Проверка нескольких сайтов concurrently"""
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, ssl=self.verify_ssl)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.check_website(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            
            return results

class MetricsVisualizer:
    def __init__(self):
        self.history = []
        
    def add_results(self, results: List[Dict]):
        """Добавление результатов для истории"""
        self.history.extend(results)
        
    def generate_status_plot(self) -> Optional[str]:
        """Генерация графика статусов"""
        if not self.history:
            return None
            
        try:
            df = pd.DataFrame(self.history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Группировка по статусам
            status_counts = df.groupby(['timestamp', 'status']).size().unstack(fill_value=0)
            
            plt.figure(figsize=(12, 6))
            status_counts.plot(kind='line', marker='o')
            plt.title('Website Status Over Time')
            plt.xlabel('Time')
            plt.ylabel('Count')
            plt.legend(title='Status')
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Сохранение в base64 для веб-отображения
            buffer = BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            image_data = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close()
            
            return image_data
            
        except Exception as e:
            logger.error(f"Error generating status plot: {e}")
            return None
    
    def generate_response_time_plot(self) -> Optional[str]:
        """Генерация графика времени ответа"""
        if not self.history:
            return None
            
        try:
            df = pd.DataFrame(self.history)
            df = df[df['response_time_ms'].notna()]
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            plt.figure(figsize=(12, 6))
            for url in df['url'].unique()[:10]:  # Ограничиваем количество линий
                url_data = df[df['url'] == url]
                plt.plot(url_data['timestamp'], url_data['response_time_ms'], 
                        marker='o', label=url[:20] + '...' if len(url) > 20 else url, 
                        linestyle='-', markersize=4)
            
            plt.title('Response Time Over Time')
            plt.xlabel('Time')
            plt.ylabel('Response Time (ms)')
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            buffer = BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight')
            buffer.seek(0)
            image_data = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close()
            
            return image_data
            
        except Exception as e:
            logger.error(f"Error generating response time plot: {e}")
            return None
    
    def generate_availability_report(self) -> Dict:
        """Генерация отчета о доступности"""
        if not self.history:
            return {}
            
        try:
            df = pd.DataFrame(self.history)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            report = {}
            for url in df['url'].unique():
                url_data = df[df['url'] == url]
                total_checks = len(url_data)
                successful_checks = len(url_data[url_data['status'] == 'up'])
                
                availability = (successful_checks / total_checks * 100) if total_checks > 0 else 0
                
                avg_response = url_data['response_time_ms'].mean()
                if pd.isna(avg_response):
                    avg_response = 0
                
                report[url] = {
                    'total_checks': total_checks,
                    'successful_checks': successful_checks,
                    'availability_percent': round(availability, 2),
                    'avg_response_time': round(avg_response, 2),
                    'last_status': url_data.iloc[-1]['status'] if not url_data.empty else 'unknown',
                    'last_check': url_data['timestamp'].max().isoformat() if not url_data.empty else 'never'
                }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating availability report: {e}")
            return {}

class WebsiteMonitor:
    def __init__(self, verify_ssl: bool = False):
        self.checker = AsyncWebsiteChecker(verify_ssl=verify_ssl)
        self.visualizer = MetricsVisualizer()
        self.verify_ssl = verify_ssl
    
    async def run_check(self, urls: List[str]) -> List[Dict]:
        """Выполнение одной проверки"""
        logger.info(f"Starting website check (SSL verification: {self.verify_ssl})...")
        
        results = await self.checker.check_multiple_websites(urls)
        self.visualizer.add_results(results)
        
        # Вывод результатов в консоль
        print("\n" + "="*80)
        print("WEBSITE MONITORING RESULTS")
        print("="*80)
        
        for result in results:
            status_icon = "✅" if result['status'] == 'up' else "❌"
            print(f"{status_icon} {result['url']}")
            print(f"   Status: {result['status']} ({result.get('status_code', 'N/A')})")
            if result.get('response_time_ms'):
                print(f"   Response: {result['response_time_ms']}ms")
            if result.get('error'):
                print(f"   Error: {result['error']}")
            print()
        
        return results
    
    def generate_report(self):
        """Генерация отчета"""
        report = self.visualizer.generate_availability_report()
        
        print("\n" + "="*80)
        print("AVAILABILITY REPORT")
        print("="*80)
        
        for url, stats in report.items():
            status_icon = "✅" if stats['availability_percent'] > 95 else "⚠️" if stats['availability_percent'] > 80 else "❌"
            print(f"{status_icon} {url}")
            print(f"   Availability: {stats['availability_percent']}%")
            print(f"   Avg Response: {stats['avg_response_time']}ms")
            print(f"   Last Status: {stats['last_status']}")
            print(f"   Last Check: {stats['last_check']}")
            print()
    
    def generate_dashboard(self):
        """Генерация HTML дашборда"""
        status_plot = self.visualizer.generate_status_plot()
        response_plot = self.visualizer.generate_response_time_plot()
        report = self.visualizer.generate_availability_report()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Website Monitoring Dashboard</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .dashboard {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }}
                .plot {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .report {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; font-weight: bold; }}
                .up {{ color: #28a745; }}
                .warning {{ color: #ffc107; }}
                .down {{ color: #dc3545; }}
                .status-icon {{ font-size: 18px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Website Monitoring Dashboard</h1>
                    <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | SSL Verification: {self.verify_ssl}</p>
                </div>
        """
        
        if status_plot or response_plot:
            html += '<div class="dashboard">'
            if status_plot:
                html += f"""
                    <div class="plot">
                        <h2>Status Overview</h2>
                        <img src="data:image/png;base64,{status_plot}" style="width:100%">
                    </div>
                """
            if response_plot:
                html += f"""
                    <div class="plot">
                        <h2>Response Times</h2>
                        <img src="data:image/png;base64,{response_plot}" style="width:100%">
                    </div>
                """
            html += '</div>'
        
        html += """
                <div class="report">
                    <h2>Availability Report</h2>
                    <table>
                        <tr>
                            <th>Website</th>
                            <th>Availability</th>
                            <th>Avg Response</th>
                            <th>Total Checks</th>
                            <th>Last Status</th>
                            <th>Last Check</th>
                        </tr>
        """
        
        for url, stats in report.items():
            status_class = 'up' if stats['availability_percent'] > 95 else 'warning' if stats['availability_percent'] > 80 else 'down'
            status_icon = "✅" if stats['availability_percent'] > 95 else "⚠️" if stats['availability_percent'] > 80 else "❌"
            
            html += f"""
                <tr>
                    <td title="{url}">{url[:50]}{'...' if len(url) > 50 else ''}</td>
                    <td class="{status_class}"><strong>{stats['availability_percent']}%</strong></td>
                    <td>{stats['avg_response_time']}ms</td>
                    <td>{stats['total_checks']}</td>
                    <td class="{status_class}">{status_icon} {stats['last_status']}</td>
                    <td>{stats['last_check']}</td>
                </tr>
            """
        
        html += """
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open('dashboard.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info("Dashboard generated: dashboard.html")
        return html

async def main():
    """Основная функция"""
    # Сайты для проверки
    websites = [
        "https://httpbin.org/status/200",
        "https://httpbin.org/status/404",
        "https://httpbin.org/status/500",
        "https://httpbin.org/json",
        "https://example.com",
        "https://google.com",
        "https://github.com"
    ]
    
    # Создаем монитор без SSL проверки (чтобы избежать ошибок сертификатов)
    monitor = WebsiteMonitor(verify_ssl=False)
    
    # Выполняем проверку
    results = await monitor.run_check(websites)
    
    # Генерируем отчет
    monitor.generate_report()
    
    # Создаем дашборд
    monitor.generate_dashboard()
    
    print("🎉 Monitoring completed! Open 'dashboard.html' to view the dashboard.")

if __name__ == "__main__":
    # Запускаем мониторинг
    asyncio.run(main())
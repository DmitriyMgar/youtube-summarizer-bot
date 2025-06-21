#!/bin/bash
# Analytics Report Runner for YouTube Summarizer Bot

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📊 YouTube Summarizer Bot Analytics${NC}"
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не найден. Установите Python3 для запуска аналитики.${NC}"
    exit 1
fi

# Check if analytics database exists
if [ ! -f "data/analytics.db" ]; then
    echo -e "${YELLOW}⚠️  База данных аналитики не найдена.${NC}"
    echo "Убедитесь, что бот запускался и генерировал логи."
    echo "База данных будет создана при первом запуске бота."
    exit 1
fi

# Default values
DAYS=30
SAVE_CHARTS=""
REPORT_ONLY=""
DB_PATH="data/analytics.db"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -d|--days)
      DAYS="$2"
      shift 2
      ;;
    -s|--save)
      SAVE_CHARTS="$2"
      shift 2
      ;;
    -r|--report-only)
      REPORT_ONLY="--report-only"
      shift
      ;;
    --db-path)
      DB_PATH="$2"
      shift 2
      ;;
    -h|--help)
      echo "Использование: $0 [опции]"
      echo ""
      echo "Опции:"
      echo "  -d, --days N        Количество дней для анализа (по умолчанию: 30)"
      echo "  -s, --save PREFIX   Сохранить графики с указанным префиксом"
      echo "  -r, --report-only   Только текстовый отчет, без графиков"
      echo "      --db-path PATH  Путь к базе данных (по умолчанию: data/analytics.db)"
      echo "  -h, --help          Показать эту справку"
      echo ""
      echo "Примеры:"
      echo "  $0                           # Стандартный отчет за 30 дней"
      echo "  $0 -d 7                      # Отчет за 7 дней"
      echo "  $0 -d 14 -s reports/weekly   # Отчет за 14 дней с сохранением графиков"
      echo "  $0 -r                        # Только текстовый отчет"
      exit 0
      ;;
    *)
      echo -e "${RED}❌ Неизвестная опция: $1${NC}"
      echo "Используйте -h или --help для справки"
      exit 1
      ;;
  esac
done

echo -e "${GREEN}🔍 Анализируем активность за ${DAYS} дней...${NC}"

# Build command
CMD="python3 analytics_report.py --days $DAYS --db-path \"$DB_PATH\""

if [ ! -z "$SAVE_CHARTS" ]; then
    CMD="$CMD --save-charts \"$SAVE_CHARTS\""
    echo -e "${GREEN}💾 Графики будут сохранены с префиксом: ${SAVE_CHARTS}${NC}"
fi

if [ ! -z "$REPORT_ONLY" ]; then
    CMD="$CMD $REPORT_ONLY"
    echo -e "${YELLOW}📄 Режим только текстового отчета${NC}"
fi

echo ""

# Run the analytics
eval $CMD

# Check if command was successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Анализ завершен успешно!${NC}"
    
    if [ ! -z "$SAVE_CHARTS" ]; then
        echo -e "${GREEN}📊 Графики сохранены в файлы с префиксом: ${SAVE_CHARTS}${NC}"
    fi
else
    echo ""
    echo -e "${RED}❌ Ошибка при выполнении анализа.${NC}"
    echo "Проверьте логи выше для подробностей."
    exit 1
fi 
#!/usr/bin/env bash
# e2e-loop.sh — запуск e2e тестів з автоматичним парсингом результату
# Використання: ./e2e-loop.sh
# Результат зберігається в e2e-report.txt (для аналізу Клодом)

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
E2E_DIR="$PROJECT_DIR/../sckandi-e2e"
REPORT_FILE="$PROJECT_DIR/e2e-report.txt"

echo "🚀 Запуск e2e тестів..."
echo "Час: $(date '+%Y-%m-%d %H:%M:%S')" > "$REPORT_FILE"
echo "==============================" >> "$REPORT_FILE"

# Запуск повного циклу
cd "$PROJECT_DIR"
make e2e-full 2>&1 | tee -a "$REPORT_FILE" || true

# Підсумок
echo "" >> "$REPORT_FILE"
echo "====== ПІДСУМОК ======" >> "$REPORT_FILE"

PASSED=$(grep -c "✓\|PASSED" "$REPORT_FILE" 2>/dev/null || echo 0)
FAILED=$(grep -c "✘\|FAILED\|failed" "$REPORT_FILE" 2>/dev/null || echo 0)

echo "✅ Пройшло: $PASSED" >> "$REPORT_FILE"
echo "❌ Впало: $FAILED" >> "$REPORT_FILE"

# Список тільки фейлурів
echo "" >> "$REPORT_FILE"
echo "====== ФЕЙЛУРИ ======" >> "$REPORT_FILE"
grep -E "FAILED|✘|Error:|assert|TimeoutError" "$REPORT_FILE" 2>/dev/null | head -100 >> "$REPORT_FILE" || true

echo ""
echo "📄 Репорт збережено: $REPORT_FILE"
echo "📊 Результат: $PASSED пройшло, $FAILED впало"

if [ "$FAILED" -gt 0 ]; then
  echo "⚠️  Є фейлури — скопіюй вміст e2e-report.txt і відправ Клоду"
  exit 1
else
  echo "🟢 Всі тести зелені!"
fi

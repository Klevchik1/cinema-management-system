// JavaScript для расчета цены с раздельными полями даты и времени
document.addEventListener('DOMContentLoaded', function() {
    console.log('Screening price calculation - improved version with date/time pickers');

    // Находим элементы
    var hallSelect = document.getElementById('id_hall');
    var priceField = document.getElementById('id_price');
    var calculationField = document.getElementById('id_price_calculation');

    // Находим новые поля даты и времени
    var dateInput = document.getElementById('id_start_date');
    var hourSelect = document.getElementById('id_start_time_0');
    var minuteSelect = document.getElementById('id_start_time_1');

    console.log('Elements found:', {
        hallSelect: !!hallSelect,
        dateInput: !!dateInput,
        hourSelect: !!hourSelect,
        minuteSelect: !!minuteSelect,
        calculationField: !!calculationField,
        priceField: !!priceField
    });

    if (!hallSelect || !dateInput || !hourSelect || !minuteSelect || !calculationField) {
        console.error('Required elements not found');
        return;
    }

    // Функция для получения времени в формате HH:MM
    function getTimeValue() {
        var hour = hourSelect.value;
        var minute = minuteSelect.value;

        if (hour && minute) {
            return hour + ':' + minute;
        }
        return null;
    }

    // Функция для расчета цены
    function calculatePrice() {
        console.log('--- Calculating price ---');

        var hallId = hallSelect.value;
        var dateValue = dateInput.value;
        var timeValue = getTimeValue();

        console.log('Values:', {
            hallId: hallId,
            date: dateValue,
            time: timeValue
        });

        if (!hallId || !dateValue || !timeValue) {
            calculationField.value = 'Выберите зал, дату и время сеанса для расчета цены';
            if (priceField) priceField.value = '';
            return;
        }

        // Определяем час из времени
        var hour = parseInt(timeValue.split(':')[0]);
        console.log('Hour extracted:', hour);

        // Получаем название зала
        var hallName = hallSelect.options[hallSelect.selectedIndex].text;
        console.log('Hall name:', hallName);

        // Определяем множитель времени
        var timeMultiplier = 1.0;
        var timeDesc = '';

        if (8 <= hour && hour < 12) {
            timeMultiplier = 0.7;
            timeDesc = 'утро (' + hour + ':00)';
        } else if (12 <= hour && hour < 16) {
            timeMultiplier = 0.9;
            timeDesc = 'день (' + hour + ':00)';
        } else if (16 <= hour && hour < 20) {
            timeMultiplier = 1.2;
            timeDesc = 'вечер (' + hour + ':00)';
        } else {
            timeMultiplier = 1.4;
            timeDesc = 'ночь (' + hour + ':00)';
        }

        console.log('Time multiplier:', timeMultiplier);

        // Определяем тип зала и базовую цену
        var hallType = 'Стандарт';
        var basePrice = 350;

        if (hallName.includes('VIP')) {
            hallType = 'VIP';
            basePrice = 1100;
        } else if (hallName.includes('Love')) {
            hallType = 'Love Hall';
            basePrice = 900;
        } else if (hallName.includes('Комфорт')) {
            hallType = 'Комфорт';
            basePrice = 550;
        } else if (hallName.includes('IMAX')) {
            hallType = 'IMAX';
            basePrice = 800;
        }

        console.log('Hall type:', hallType, 'Base price:', basePrice);

        // Рассчитываем итоговую цену
        var finalPrice = Math.round(basePrice * timeMultiplier);
        console.log('Final price:', finalPrice);

        // Формируем красивый текст расчета
        var calculationText =
            '╔══════════════════════════════════════════════╗\n' +
            '║      📊 РАСЧЕТ СТОИМОСТИ БИЛЕТА             ║\n' +
            '╚══════════════════════════════════════════════╝\n\n' +
            '• Зал: "' + hallName + '"\n' +
            '  └── Тип: ' + hallType + '\n' +
            '  └── Базовая цена: ' + basePrice + ' руб.\n\n' +
            '• Время сеанса: ' + timeDesc + '\n' +
            '  └── Множитель времени: ×' + timeMultiplier + '\n\n' +
            '══════════════════════════════════════════════\n' +
            '  ФОРМУЛА: ' + basePrice + ' руб. × ' + timeMultiplier + '\n' +
            '  ИТОГО: ' + finalPrice + ' руб.\n' +
            '══════════════════════════════════════════════\n\n' +
            '📝 Цена будет зафиксирована при сохранении';

        // Обновляем поля
        calculationField.value = calculationText;

        if (priceField) {
            priceField.value = finalPrice;
            console.log('Price field updated to:', priceField.value);

            // Добавляем CSS класс для визуального выделения
            priceField.style.backgroundColor = '#e8f5e8';
            priceField.style.color = '#155724';
            priceField.style.borderColor = '#c3e6cb';
            priceField.style.fontWeight = 'bold';

            // Для темной темы
            if (document.documentElement.getAttribute('data-theme') === 'dark' ||
                window.matchMedia('(prefers-color-scheme: dark)').matches) {
                priceField.style.backgroundColor = '#1a472a';
                priceField.style.color = '#90ee90';
                priceField.style.borderColor = '#2e8b57';
            }
        }

        console.log('--- Calculation completed ---');
    }

    // Добавляем обработчики событий
    hallSelect.addEventListener('change', calculatePrice);
    dateInput.addEventListener('change', calculatePrice);
    hourSelect.addEventListener('change', calculatePrice);
    minuteSelect.addEventListener('change', calculatePrice);

    // Запускаем расчет при загрузке
    setTimeout(calculatePrice, 500);

    // Обновляем расчет при фокусе на полях
    dateInput.addEventListener('focus', function() {
        setTimeout(calculatePrice, 100);
    });

    console.log('Event listeners attached for improved time picker');
});
// JavaScript для расчета цены с раздельными полями даты и времени
document.addEventListener('DOMContentLoaded', function() {
    console.log('Screening price calculation - final version');

    // Находим элементы
    var hallSelect = document.getElementById('id_hall');
    var priceField = document.getElementById('id_price');
    var calculationField = document.getElementById('id_price_calculation');

    // Находим поля даты и времени (стандартные Django виджеты)
    var dateInput = document.getElementById('id_start_time_0');
    var timeInput = document.getElementById('id_start_time_1');

    console.log('Elements found:', {
        hallSelect: !!hallSelect,
        dateInput: !!dateInput,
        timeInput: !!timeInput,
        calculationField: !!calculationField,
        priceField: !!priceField
    });

    // Если нет поля времени с id, ищем по имени
    if (!timeInput) {
        timeInput = document.querySelector('select[name="start_time_1"]');
    }

    // Если нет поля даты с id, ищем по имени
    if (!dateInput) {
        dateInput = document.querySelector('input[name="start_time_0"]');
    }

    if (!hallSelect || !dateInput || !timeInput || !calculationField) {
        console.error('Required elements not found');
        return;
    }

    // Функция для расчета цены
    function calculatePrice() {
        console.log('--- Calculating price ---');

        var hallId = hallSelect.value;
        var dateValue = dateInput.value;
        var timeValue = timeInput.value;

        console.log('Values:', {
            hallId: hallId,
            date: dateValue,
            time: timeValue
        });

        if (!hallId || !dateValue || !timeValue) {
            calculationField.value = 'Выберите зал и время сеанса для расчета цены';
            if (priceField) priceField.value = '';
            return;
        }

        // Определяем час из времени
        var hour = 12;
        if (timeValue && timeValue.includes(':')) {
            hour = parseInt(timeValue.split(':')[0]);
        } else if (timeValue) {
            // Для выпадающего списка (формат "19:30:00")
            hour = parseInt(timeValue);
        }

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

        // Формируем текст расчета
        var calculationText =
            '📊 РАСЧЕТ СТОИМОСТИ БИЛЕТА:\n' +
            '──────────────────────────\n' +
            '• Зал: "' + hallName + '" → тип: ' + hallType + '\n' +
            '• Базовая цена: ' + basePrice + ' руб.\n' +
            '• Время сеанса: ' + timeDesc + '\n' +
            '• Множитель времени: ' + timeMultiplier + '\n' +
            '──────────────────────────\n' +
            '• ИТОГО: ' + basePrice + ' × ' + timeMultiplier + ' = ' + finalPrice + ' руб.\n' +
            '──────────────────────────\n' +
            '*Цена фиксируется при сохранении';

        // Обновляем поля
        calculationField.value = calculationText;

        if (priceField) {
            priceField.value = finalPrice;
            console.log('Price field updated to:', priceField.value);
        }

        console.log('--- Calculation completed ---');
    }

    // Добавляем обработчики событий
    hallSelect.addEventListener('change', calculatePrice);
    dateInput.addEventListener('change', calculatePrice);
    timeInput.addEventListener('change', calculatePrice);

    // Также отслеживаем ввод вручную (если поле текстовое)
    if (dateInput.type === 'text') {
        dateInput.addEventListener('input', function() {
            clearTimeout(window.dateTimeout);
            window.dateTimeout = setTimeout(calculatePrice, 300);
        });
    }

    // Для select поля времени
    if (timeInput.tagName === 'SELECT') {
        // Уже есть change обработчик
    } else if (timeInput.type === 'text') {
        timeInput.addEventListener('input', function() {
            clearTimeout(window.timeTimeout);
            window.timeTimeout = setTimeout(calculatePrice, 300);
        });
    }

    // Запускаем расчет при загрузке
    setTimeout(calculatePrice, 500);

    // Дополнительно: отслеживаем изменения в календаре (если он открывается)
    var calendarLinks = document.querySelectorAll('.datetimeshortcuts a');
    calendarLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            setTimeout(calculatePrice, 1000);
        });
    });

    // Обновляем расчет при фокусе на полях
    dateInput.addEventListener('focus', function() {
        setTimeout(calculatePrice, 100);
    });

    timeInput.addEventListener('focus', function() {
        setTimeout(calculatePrice, 100);
    });

    console.log('Event listeners attached');
});
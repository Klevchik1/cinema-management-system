document.addEventListener('DOMContentLoaded', function() {
    // Эффект киноплёнки для шапки
    const header = document.getElementById('header');
    if (header) {
        header.style.position = 'relative';
        header.style.overflow = 'hidden';

        // Создаём эффект плёнки
        const filmEffect = document.createElement('div');
        filmEffect.style.position = 'absolute';
        filmEffect.style.top = '0';
        filmEffect.style.left = '0';
        filmEffect.style.width = '100%';
        filmEffect.style.height = '100%';
        filmEffect.style.background = 'repeating-linear-gradient(90deg, transparent, transparent 20px, rgba(255, 204, 0, 0.1) 20px, rgba(255, 204, 0, 0.1) 40px)';
        filmEffect.style.pointerEvents = 'none';
        filmEffect.style.zIndex = '1';
        header.appendChild(filmEffect);
    }

    // Анимация карточек при наведении
    const cards = document.querySelectorAll('.module, .form-row, .inline-group');
    cards.forEach(card => {
        card.style.transition = 'all 0.3s ease';
        card.addEventListener('mouseenter', function() {
            this.style.boxShadow = '0 0 20px rgba(255, 0, 0, 0.6)';
            this.style.transform = 'translateY(-2px)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.boxShadow = '';
            this.style.transform = '';
        });
    });

    // Подсветка обязательных полей
    const requiredFields = document.querySelectorAll('input[required], select[required]');
    requiredFields.forEach(field => {
        const label = document.querySelector(`label[for="${field.id}"]`);
        if (label) {
            label.innerHTML += ' <span style="color: #ff0000; font-weight: bold;">*</span>';
        }
    });

    // Кастомные уведомления
    const addMessage = (text, type = 'info') => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `cinema-message cinema-message-${type}`;
        messageDiv.innerHTML = `
            <div style="
                background: ${type === 'success' ? 'rgba(76, 175, 80, 0.2)' : 
                               type === 'error' ? 'rgba(244, 67, 54, 0.2)' : 
                               'rgba(255, 0, 0, 0.2)'};
                border: 1px solid ${type === 'success' ? '#4CAF50' : 
                                   type === 'error' ? '#f44336' : 
                                   '#ff0000'};
                color: #fff;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
                animation: fadeIn 0.5s ease;
            ">
                ${text}
                <button onclick="this.parentElement.remove()" style="
                    float: right;
                    background: none;
                    border: none;
                    color: #ffcc00;
                    cursor: pointer;
                    font-size: 16px;
                ">×</button>
            </div>
        `;

        const content = document.querySelector('#content');
        if (content) {
            content.prepend(messageDiv);
        }
    };

    // Глобальная функция для показа сообщений
    window.cinemaMessage = addMessage;
});
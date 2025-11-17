const CATEGORY_RANGES = {
    'stoichiometry': [1, 6],
    'descriptive': [7, 12],
    'states': [13, 18],
    'thermodynamics': [19, 24],
    'kinetics': [25, 30],
    'equilibrium': [31, 36],
    'redox': [37, 42],
    'atomic': [43, 48],
    'bonding': [49, 54],
    'organic': [55, 60]
};

const CATEGORY_NAMES = {
    'stoichiometry': 'Stoichiometry/\n Solutions',
    'descriptive': 'Descriptive/\nLaboratory',
    'states': 'States\nof\nMatter',
    'thermodynamics': 'Thermodynamics',
    'kinetics': 'Kinetics',
    'equilibrium': 'Equilibrium',
    'redox': 'Oxidation-\nReduction',
    'atomic': 'Atomic Structure/\nPeriodicity',
    'bonding': 'Bonding/\nMolecular\nStructure',
    'organic': 'Organic/\nBiochemistry'
};

let currentQuestionIndex = 0;
let questions = [];
let allQuestions = []; // Store all questions for random mode
let mode = 'random'; // 'random', 'exam', or 'category'
let examType = 'local';
let examYear = '2023';
let category = null;
let answered = new Set();
let correctCount = 0;
let attemptedCount = 0;

const preloadedImages = new Map();
const PRELOAD_COUNT = 10;
const PRELOAD_ALL_THRESHOLD = 60;

document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    mode = urlParams.get('mode') || 'random';
    examType = urlParams.get('type') || 'local';
    examYear = urlParams.get('year') || '2023';
    category = urlParams.get('category');

    await loadQuestions();
    preloadUpcomingImages();
    displayQuestion();
    setupEventListeners();
});

async function loadQuestions() {
    try {
        if (mode === 'category' && category) {
            const categoryRange = CATEGORY_RANGES[category];
            const categoryName = CATEGORY_NAMES[category];

            if (!categoryRange) {
                throw new Error(`Invalid category: ${category}`);
            }

            const response = await fetch('dropbox_question_links.json');
            if (!response.ok) {
                throw new Error(`Failed to load questions: ${response.status}`);
            }
            allQuestions = await response.json();

            const [minQ, maxQ] = categoryRange;
            questions = allQuestions.filter(q => {
                const qNum = q.question_number;
                return qNum >= minQ && qNum <= maxQ && q.answer && q.answer.trim() !== '';
            });

            shuffleArray(questions);
            const examInfo = document.getElementById('exam-info');
            examInfo.textContent = categoryName || 'Category Questions';
            const totalQuestionsEl = document.getElementById('question-counter');
            if (totalQuestionsEl) {
                totalQuestionsEl.textContent = `Total questions: ${questions.length}`;
            }
            console.log(`Loaded ${questions.length} questions for category: ${categoryName} (Q${minQ}-${maxQ} across all years)`);
        } else if (mode === 'random') {
            const response = await fetch('dropbox_question_links.json');
            if (!response.ok) {
                throw new Error(`Failed to load questions: ${response.status}`);
            }
            allQuestions = await response.json();
            allQuestions = allQuestions.filter(q => q.answer && q.answer.trim() !== '');
            shuffleArray(allQuestions);
            questions = allQuestions;
            const examInfo = document.getElementById('exam-info');
            examInfo.textContent = 'Random Questions';
            const totalQuestionsEl = document.getElementById('question-counter');
            if (totalQuestionsEl) {
                totalQuestionsEl.textContent = `Total questions: ${questions.length}`;
            }
            console.log(`Loaded ${questions.length} random questions`);
        } else {
            const response = await fetch(`parsed_exams/${examYear}/${examType}_answer_key.json`);
            if (!response.ok) {
                throw new Error(`Failed to load questions: ${response.status}`);
            }
            const examQuestions = await response.json();
            const dropboxResponse = await fetch('dropbox_question_links.json');
            const dropboxLinks = await dropboxResponse.json();
            const linkMap = {};

            dropboxLinks.forEach(item => {
                linkMap[item.local_path] = item.direct_link;
            });

            questions = examQuestions.map(q => ({
                ...q,
                direct_link: linkMap[q.image_path] || null
            }));
            const examInfo = document.getElementById('exam-info');
            const examTypeDisplay = examType === 'local' ? 'Local' : 'National';
            examInfo.textContent = `${examYear} ${examTypeDisplay} Exam`;
            console.log(`Loaded ${questions.length} questions from ${examYear} ${examType} exam`);
        }
    } catch (error) {
        console.error('Error loading questions:', error);
        alert('Failed to load questions. Please try again.');
    }
}

// Shuffle array using Fisher-Yates algorithm
function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

function preloadImage(url) {
    if (!url || preloadedImages.has(url)) {
        return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            preloadedImages.set(url, img);
            resolve(img);
        };
        img.onerror = () => {
            console.warn('Failed to preload image:', url);
            reject();
        };
        img.src = url;
    });
}

// Preload upcoming images (bidirectional)
function preloadUpcomingImages() {
    if (questions.length <= PRELOAD_ALL_THRESHOLD) {
        console.log(`Preloading all ${questions.length} images for this session...`);
        for (let i = 0; i < questions.length; i++) {
            const question = questions[i];
            const imageUrl = question.direct_link || question.image_path || question.local_path;

            if (imageUrl) {
                preloadImage(imageUrl).catch(() => {});
            }
        }
        return;
    }
    const startIdx = Math.max(0, currentQuestionIndex - PRELOAD_COUNT);
    const endIdx = Math.min(currentQuestionIndex + PRELOAD_COUNT + 1, questions.length);

    for (let i = startIdx; i < endIdx; i++) {
        const question = questions[i];
        const imageUrl = question.direct_link || question.image_path || question.local_path;
        if (imageUrl) {
            preloadImage(imageUrl).catch(() => {});
        }
    }
}

function displayQuestion() {
    if (questions.length === 0) return;
    const question = questions[currentQuestionIndex];
    const currentQuestionEl = document.getElementById('current-question-number');

    if (currentQuestionEl) {
        currentQuestionEl.textContent = `Questions this session: ${currentQuestionIndex + 1}`;
    }

    const detailsElement = document.getElementById('question-details');
    if (detailsElement && (mode === 'random' || mode === 'category')) {
        const year = question.exam_year || '?';
        const type = question.exam_type === 'local' ? 'Local' : question.exam_type === 'national' ? 'National' : '?';
        const qNum = question.question_number || '?';
        detailsElement.textContent = `${year} ${type} — Q${qNum}`;
    } else if (detailsElement) {
        detailsElement.textContent = '';
    }

    const img = document.getElementById('question-image');
    let imageUrl = null;
    if (question.direct_link) {
        imageUrl = question.direct_link;
    } else if (question.image_path) {
        imageUrl = question.image_path;
    } else if (question.local_path) {
        imageUrl = question.local_path;
    }
    img.onerror = function() {
        console.error('Failed to load image:', img.src);

        if (img.src === question.direct_link && question.local_path) {
            console.log('Trying local path fallback:', question.local_path);
            img.src = question.local_path;
        } else {
            img.alt = 'Failed to load image';
        }
    };

    if (imageUrl && preloadedImages.has(imageUrl)) {
        const preloadedImg = preloadedImages.get(imageUrl);
        img.src = preloadedImg.src;
    } else if (imageUrl) {
        img.src = imageUrl;
    } else {
        console.error('No valid image source found for question:', question);
    }

    const questionNum = question.question_number || currentQuestionIndex + 1;
    const year = question.exam_year || 'Unknown';
    const type = question.exam_type || '';
    img.alt = `${year} ${type} Question ${questionNum}`;
    resetAnswerButtons();
    const feedback = document.getElementById('feedback');
    feedback.className = 'feedback hidden';
    updateNavigationButtons();
    updateScore();
    preloadUpcomingImages();
}

function setupEventListeners() {
    const answerButtons = document.querySelectorAll('.answer-btn');
    answerButtons.forEach(btn => {
        btn.addEventListener('click', () => handleAnswer(btn.dataset.answer));
    });

    document.getElementById('prev-btn').addEventListener('click', previousQuestion);
    document.getElementById('next-btn').addEventListener('click', nextQuestion);
}

function handleAnswer(selectedAnswer) {
    const question = questions[currentQuestionIndex];
    const correctAnswer = question.answer;

    let questionKey;
    if (mode === 'category') {
        questionKey = `category-${category}-${currentQuestionIndex}`;
    } else if (mode === 'random') {
        questionKey = `random-${currentQuestionIndex}`;
    } else {
        questionKey = `${examYear}-${examType}-${currentQuestionIndex}`;
    }

    if (answered.has(questionKey)) {
        return;
    }

    answered.add(questionKey);
    attemptedCount++;

    const isCorrect = selectedAnswer === correctAnswer;
    if (isCorrect) {
        correctCount++;
    }

    const answerButtons = document.querySelectorAll('.answer-btn');
    answerButtons.forEach(btn => {
        btn.disabled = true;

        if (btn.dataset.answer === correctAnswer) {
            btn.classList.add('correct');
        }

        if (btn.dataset.answer === selectedAnswer && !isCorrect) {
            btn.classList.add('incorrect');
        }
    });

    const feedback = document.getElementById('feedback');
    feedback.className = `feedback ${isCorrect ? 'correct' : 'incorrect'}`;
    feedback.textContent = isCorrect
        ? 'Correct!'
        : `Incorrect. The correct answer is ${correctAnswer}.`;
    updateScore();
}

function resetAnswerButtons() {
    const answerButtons = document.querySelectorAll('.answer-btn');

    let questionKey;
    if (mode === 'category') {
        questionKey = `category-${category}-${currentQuestionIndex}`;
    } else if (mode === 'random') {
        questionKey = `random-${currentQuestionIndex}`;
    } else {
        questionKey = `${examYear}-${examType}-${currentQuestionIndex}`;
    }

    const isAnswered = answered.has(questionKey);

    answerButtons.forEach(btn => {
        btn.classList.remove('correct', 'incorrect');
        btn.disabled = isAnswered;

        if (isAnswered) {
            const question = questions[currentQuestionIndex];
            const correctAnswer = question.answer;

            if (btn.dataset.answer === correctAnswer) {
                btn.classList.add('correct');
            }
        }
    });
}

function updateNavigationButtons() {
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    prevBtn.disabled = currentQuestionIndex === 0;
    nextBtn.disabled = currentQuestionIndex === questions.length - 1;
}

function updateScore() {
    const scoreElement = document.getElementById('score');
    const percentageElement = document.getElementById('percentage');
    const correctBar = document.getElementById('progress-bar-correct');
    const incorrectBar = document.getElementById('progress-bar-incorrect');
    scoreElement.textContent = `Correct: ${correctCount} / ${attemptedCount}`;

    if (attemptedCount > 0) {
        const percentage = Math.round((correctCount / attemptedCount) * 100);
        const incorrectCount = attemptedCount - correctCount;
        const incorrectPercentage = Math.round((incorrectCount / attemptedCount) * 100);

        percentageElement.textContent = `${percentage}% correct`;

        if (correctBar && incorrectBar) {
            correctBar.style.width = `${percentage}%`;
            incorrectBar.style.width = `${incorrectPercentage}%`;
        }
    } else {
        percentageElement.textContent = '';
        if (correctBar && incorrectBar) {
            correctBar.style.width = '0%';
            incorrectBar.style.width = '0%';
        }
    }
}

function previousQuestion() {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        displayQuestion();
    }
}

function nextQuestion() {
    if (currentQuestionIndex < questions.length - 1) {
        currentQuestionIndex++;
        displayQuestion();
    }
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
        previousQuestion();
    } else if (e.key === 'ArrowRight') {
        nextQuestion();
    }

    let questionKey;
    if (mode === 'category') {
        questionKey = `category-${category}-${currentQuestionIndex}`;
    } else if (mode === 'random') {
        questionKey = `random-${currentQuestionIndex}`;
    } else {
        questionKey = `${examYear}-${examType}-${currentQuestionIndex}`;
    }

    if (!answered.has(questionKey)) {
        if (e.key === '1') handleAnswer('A');
        else if (e.key === '2') handleAnswer('B');
        else if (e.key === '3') handleAnswer('C');
        else if (e.key === '4') handleAnswer('D');
    }
});

// Questions Viewer JavaScript

// Configuration - UPDATE THIS with your Dropbox base URL once images are uploaded
const CONFIG = {
    // Set to true when using Dropbox, false for local images
    useDropbox: false,

    // Your Dropbox folder URL base (replace with actual URL after upload)
    // Example: 'https://dl.dropboxusercontent.com/your-folder/question_images'
    dropboxBaseUrl: '',

    // Local path for development
    localBasePath: 'question_images'
};

// Current state
let currentQuestionIndex = 0;
let questions = [];
let examType = 'local'; // default
let examYear = '2023'; // default
let answered = new Set();
let correctCount = 0;
let attemptedCount = 0;

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    // Get exam parameters from URL
    const urlParams = new URLSearchParams(window.location.search);
    examType = urlParams.get('type') || 'local';
    examYear = urlParams.get('year') || '2023';

    // Load questions
    await loadQuestions();

    // Display first question
    displayQuestion();

    // Setup event listeners
    setupEventListeners();
});

// Load questions from answer key JSON
async function loadQuestions() {
    try {
        const response = await fetch(`parsed_exams/${examYear}/${examType}_answer_key.json`);
        if (!response.ok) {
            throw new Error(`Failed to load questions: ${response.status}`);
        }
        questions = await response.json();

        // Update exam info
        const examInfo = document.getElementById('exam-info');
        const examTypeDisplay = examType === 'local' ? 'Local' : 'National';
        examInfo.textContent = `${examYear} ${examTypeDisplay} Exam`;

        console.log(`Loaded ${questions.length} questions from ${examYear} ${examType} exam`);
    } catch (error) {
        console.error('Error loading questions:', error);
        alert('Failed to load questions. Please try again.');
    }
}

// Display current question
function displayQuestion() {
    if (questions.length === 0) return;

    const question = questions[currentQuestionIndex];

    // Update question counter
    const counter = document.getElementById('question-counter');
    counter.textContent = `Question ${currentQuestionIndex + 1}`;

    // Update image source
    const img = document.getElementById('question-image');
    const imagePath = getImageUrl(question.image_path);
    img.src = imagePath;
    img.alt = `Question ${question.question_number}`;

    // Reset answer buttons
    resetAnswerButtons();

    // Update feedback
    const feedback = document.getElementById('feedback');
    feedback.className = 'feedback hidden';

    // Update navigation buttons
    updateNavigationButtons();

    // Update score
    updateScore();
}

// Get image URL (Dropbox or local)
function getImageUrl(imagePath) {
    if (CONFIG.useDropbox) {
        // Convert local path to Dropbox URL
        // Remove 'question_images/' prefix if present
        const relativePath = imagePath.replace('question_images/', '');
        return `${CONFIG.dropboxBaseUrl}/${relativePath}`;
    } else {
        // Use local path
        return imagePath;
    }
}

// Setup event listeners
function setupEventListeners() {
    // Answer buttons
    const answerButtons = document.querySelectorAll('.answer-btn');
    answerButtons.forEach(btn => {
        btn.addEventListener('click', () => handleAnswer(btn.dataset.answer));
    });

    // Navigation buttons
    document.getElementById('prev-btn').addEventListener('click', previousQuestion);
    document.getElementById('next-btn').addEventListener('click', nextQuestion);
}

// Handle answer selection
function handleAnswer(selectedAnswer) {
    const question = questions[currentQuestionIndex];
    const correctAnswer = question.answer;
    const questionKey = `${examYear}-${examType}-${currentQuestionIndex}`;

    // If already answered, don't allow re-answering
    if (answered.has(questionKey)) {
        return;
    }

    // Mark as answered
    answered.add(questionKey);
    attemptedCount++;

    // Check if correct
    const isCorrect = selectedAnswer === correctAnswer;
    if (isCorrect) {
        correctCount++;
    }

    // Update button states
    const answerButtons = document.querySelectorAll('.answer-btn');
    answerButtons.forEach(btn => {
        btn.disabled = true;

        // Highlight correct answer
        if (btn.dataset.answer === correctAnswer) {
            btn.classList.add('correct');
        }

        // Highlight incorrect selection
        if (btn.dataset.answer === selectedAnswer && !isCorrect) {
            btn.classList.add('incorrect');
        }
    });

    // Show feedback
    const feedback = document.getElementById('feedback');
    feedback.className = `feedback ${isCorrect ? 'correct' : 'incorrect'}`;
    feedback.textContent = isCorrect
        ? 'Correct!'
        : `Incorrect. The correct answer is ${correctAnswer}.`;

    // Update score
    updateScore();
}

// Reset answer buttons
function resetAnswerButtons() {
    const answerButtons = document.querySelectorAll('.answer-btn');
    const questionKey = `${examYear}-${examType}-${currentQuestionIndex}`;
    const isAnswered = answered.has(questionKey);

    answerButtons.forEach(btn => {
        btn.classList.remove('correct', 'incorrect');
        btn.disabled = isAnswered;

        // If already answered, show the result
        if (isAnswered) {
            const question = questions[currentQuestionIndex];
            const correctAnswer = question.answer;

            if (btn.dataset.answer === correctAnswer) {
                btn.classList.add('correct');
            }
        }
    });
}

// Update navigation buttons
function updateNavigationButtons() {
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');

    prevBtn.disabled = currentQuestionIndex === 0;
    nextBtn.disabled = currentQuestionIndex === questions.length - 1;
}

// Update score display
function updateScore() {
    const scoreElement = document.getElementById('score');
    scoreElement.textContent = `Correct: ${correctCount} / ${attemptedCount}`;

    if (attemptedCount > 0) {
        const percentage = Math.round((correctCount / attemptedCount) * 100);
        scoreElement.textContent += ` (${percentage}%)`;
    }
}

// Previous question
function previousQuestion() {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex--;
        displayQuestion();
    }
}

// Next question
function nextQuestion() {
    if (currentQuestionIndex < questions.length - 1) {
        currentQuestionIndex++;
        displayQuestion();
    }
}

// Keyboard navigation
document.addEventListener('keydown', (e) => {
    // Arrow keys for navigation
    if (e.key === 'ArrowLeft') {
        previousQuestion();
    } else if (e.key === 'ArrowRight') {
        nextQuestion();
    }

    // Number keys for answers (1-4 = A-D)
    const questionKey = `${examYear}-${examType}-${currentQuestionIndex}`;
    if (!answered.has(questionKey)) {
        if (e.key === '1') handleAnswer('A');
        else if (e.key === '2') handleAnswer('B');
        else if (e.key === '3') handleAnswer('C');
        else if (e.key === '4') handleAnswer('D');
    }
});

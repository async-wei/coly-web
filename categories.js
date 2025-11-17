const categories = [
    {
        number: '01',
        text: 'Stoichiometry/Solutions',
        slug: 'stoichiometry',
        questionRange: [1, 6]
    },
    {
        number: '02',
        text: 'Descriptive/Laboratory',
        slug: 'descriptive',
        questionRange: [7, 12]
    },
    {
        number: '03',
        text: 'States of Matter',
        slug: 'states',
        questionRange: [13, 18]
    },
    {
        number: '04',
        text: 'Thermodynamics',
        slug: 'thermodynamics',
        questionRange: [19, 24]
    },
    {
        number: '05',
        text: 'Kinetics',
        slug: 'kinetics',
        questionRange: [25, 30]
    },
    {
        number: '06',
        text: 'Equilibrium',
        slug: 'equilibrium',
        questionRange: [31, 36]
    },
    {
        number: '07',
        text: 'Oxidation-Reduction',
        slug: 'redox',
        questionRange: [37, 42]
    },
    {
        number: '08',
        text: 'Atomic Structure/Periodicity',
        slug: 'atomic',
        questionRange: [43, 48]
    },
    {
        number: '09',
        text: 'Bonding/Molecular Structure',
        slug: 'bonding',
        questionRange: [49, 54]
    },
    {
        number: '10',
        text: 'Organic/Biochemistry',
        slug: 'organic',
        questionRange: [55, 60]
    }
];

function createCategoryItem(category) {
    const li = document.createElement('li');
    li.className = 'category-item';
    const link = document.createElement('a');
    link.className = 'category-link';
    link.href = `questions.html?mode=category&category=${category.slug}`;
    const content = document.createElement('div');
    content.className = 'category-content';
    const text = document.createElement('div');
    text.className = 'category-text';
    text.innerHTML = category.text.replace(/\//g, '/<br>');
    const number = document.createElement('sup');
    number.className = 'category-number';
    number.textContent = category.number;
    content.appendChild(text);
    content.appendChild(number);
    link.appendChild(content);
    li.appendChild(link);
    return li;
}

function initializeCategories() {
    const categoriesList = document.getElementById('categories-list');
    if (!categoriesList) {
        console.error('Categories list container not found');
        return;
    }
    categories.forEach(category => {
        const categoryItem = createCategoryItem(category);
        categoriesList.appendChild(categoryItem);
    });
    console.log(`Initialized ${categories.length} categories`);
}

if (typeof window !== 'undefined') {
    window.CHEMISTRY_CATEGORIES = categories;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeCategories);
} else {
    initializeCategories();
}

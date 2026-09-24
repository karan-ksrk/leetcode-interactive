// LeetCode Interactive — Problem browser

let allProblems = [];

async function loadProblems() {
    try {
        const response = await fetch('./problems.json');
        if (!response.ok) {
            console.error('Failed to load problems.json');
            return [];
        }
        allProblems = await response.json();
        return allProblems;
    } catch (error) {
        console.error('Error loading problems:', error);
        return [];
    }
}

function extractTopics(problems) {
    const topics = new Set();
    problems.forEach(p => {
        if (p.topics && Array.isArray(p.topics)) {
            p.topics.forEach(t => topics.add(t));
        }
    });
    return Array.from(topics).sort();
}

function populateTopicFilter() {
    const topics = extractTopics(allProblems);
    const select = document.getElementById('topic-filter');

    topics.forEach(topic => {
        const option = document.createElement('option');
        option.value = topic;
        option.textContent = topic;
        select.appendChild(option);
    });
}

function applyFilters() {
    const searchText = document.getElementById('search-input').value.toLowerCase();
    const difficultyFilter = document.getElementById('difficulty-filter').value;
    const topicFilter = document.getElementById('topic-filter').value;

    let filtered = allProblems.filter(problem => {
        // Search by title or problem number
        const matchesSearch = !searchText ||
            problem.title.toLowerCase().includes(searchText) ||
            String(problem.id).includes(searchText);

        // Difficulty filter
        const matchesDifficulty = !difficultyFilter ||
            problem.difficulty === difficultyFilter;

        // Topic filter
        const matchesTopic = !topicFilter ||
            (problem.topics && problem.topics.includes(topicFilter));

        return matchesSearch && matchesDifficulty && matchesTopic;
    });

    renderProblems(filtered);
    updateProblemCount(filtered.length, allProblems.length);
}

function renderProblems(problems) {
    const grid = document.getElementById('problem-grid');
    const emptyState = document.getElementById('empty-state');

    grid.innerHTML = '';

    if (problems.length === 0) {
        emptyState.removeAttribute('hidden');
        return;
    }

    emptyState.setAttribute('hidden', '');

    problems.forEach(problem => {
        const card = document.createElement('a');
        card.className = 'problem-card';
        card.href = `./${problem.file}`;

        const difficultyClass = `difficulty-${problem.difficulty.toLowerCase()}`;

        const topicsHtml = problem.topics && problem.topics.length
            ? problem.topics.map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join('')
            : '';

        card.innerHTML = `
            <span class="problem-number">#${problem.id}</span>
            <h3 class="problem-title">${escapeHtml(problem.title)}</h3>
            <div class="problem-meta">
                <span class="difficulty-badge ${difficultyClass}">${escapeHtml(problem.difficulty)}</span>
            </div>
            <div class="topic-list">${topicsHtml}</div>
            <div class="problem-link">View Explanation →</div>
        `;

        grid.appendChild(card);
    });
}

function updateProblemCount(filtered, total) {
    const badge = document.getElementById('problem-count');
    if (filtered === total) {
        badge.textContent = `${total} problem${total !== 1 ? 's' : ''}`;
    } else {
        badge.textContent = `${filtered} of ${total} problem${total !== 1 ? 's' : ''}`;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(fn, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn(...args), delay);
    };
}

async function init() {
    await loadProblems();
    populateTopicFilter();

    const searchInput = document.getElementById('search-input');
    const difficultyFilter = document.getElementById('difficulty-filter');
    const topicFilter = document.getElementById('topic-filter');

    const debouncedApplyFilters = debounce(applyFilters, 150);

    searchInput.addEventListener('input', debouncedApplyFilters);
    difficultyFilter.addEventListener('change', applyFilters);
    topicFilter.addEventListener('change', applyFilters);

    applyFilters();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

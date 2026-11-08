// Monthly Expenses Bar Chart
const expenseCanvas = document.getElementById("expenseChart");

if (expenseCanvas) {
    new Chart(expenseCanvas, {
        type: "bar",

        data: {
            labels: monthlyLabels,

            datasets: [{
                label: "Monthly Expenses (₹)",
                data: monthlyTotals,
                backgroundColor: "#7162e8",
                borderRadius: 8
            }]
        },

        options: {
            responsive: true,

            plugins: {
                legend: {
                    display: false
                }
            },

            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}


// Category Expenses Doughnut Chart
const categoryCanvas = document.getElementById("categoryChart");

if (categoryCanvas) {
    new Chart(categoryCanvas, {
        type: "doughnut",

        data: {
            labels: categoryLabels,

            datasets: [{
                data: categoryTotals,

                backgroundColor: [
                    "#7162e8",
                    "#22c55e",
                    "#f59e0b",
                    "#ec4899",
                    "#38bdf8",
                    "#a78bfa"
                ],

                borderWidth: 0
            }]
        },

        options: {
            responsive: true,

            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });
}
// Dark Mode Toggle

const themeToggle = document.getElementById("themeToggle");

if (themeToggle) {
    themeToggle.addEventListener("click", function () {
        document.body.classList.toggle("dark-mode");

        if (document.body.classList.contains("dark-mode")) {
            localStorage.setItem("theme", "dark");
            themeToggle.innerHTML = "☀️ Light Mode";
        } else {
            localStorage.setItem("theme", "light");
            themeToggle.innerHTML = "🌙 Dark Mode";
        }
    });
}
// Load Saved Theme

const savedTheme = localStorage.getItem("theme");

if (savedTheme === "dark") {
    document.body.classList.add("dark-mode");

    const themeButton = document.getElementById("themeToggle");

    if (themeButton) {
        themeButton.innerHTML = "☀️ Light Mode";
    }
}
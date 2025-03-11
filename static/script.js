$(document).ready(function () {
    $("#stockForm").submit(function (event) {
        event.preventDefault();
        let ticker = $("#ticker").val().trim().toUpperCase();

        if (ticker === "") {
            alert("Please enter a stock ticker.");
            return;
        }

        // Show loading animation
        $("#button-text").addClass("d-none");
        $("#loading-spinner").removeClass("d-none");
        $("#stockForm button").prop("disabled", true);

        $.ajax({
            url: "/analyze",
            type: "POST",
            data: { ticker: ticker },
            beforeSend: function () {
                $("#resultBox").hide();
                $("#resultContent").html("<p class='text-light'>Loading analysis...</p>");
            },
            success: function (response) {
                if (response.error) {
                    $("#resultContent").html(`<div class="alert alert-danger">${response.error}</div>`);
                } else {
                    $("#resultContent").html(response.result);
                    $("#disclaimer").html(response.disclaimer);

                    // Render stock chart
                    if (response.plot_data && response.plot_data.dates.length > 0) {
                        renderStockChart(response.plot_data, ticker);
                    } else {
                        $("#stockGraph").html("<p class='text-warning'>No stock data available for chart.</p>");
                    }

                    $("#resultBox").fadeIn();
                }
            },
            complete: function () {
                $("#button-text").removeClass("d-none");
                $("#loading-spinner").addClass("d-none");
                $("#stockForm button").prop("disabled", false);
            },
            error: function () {
                $("#resultContent").html(`<div class="alert alert-danger">Error retrieving stock data.</div>`);
                $("#button-text").removeClass("d-none");
                $("#loading-spinner").addClass("d-none");
                $("#stockForm button").prop("disabled", false);
            }
        });
    });

    function renderStockChart(data, ticker) {
        const traceCandlestick = {
            x: data.dates,
            open: data.open,
            high: data.high,
            low: data.low,
            close: data.close,
            type: "candlestick",
            name: `${ticker} Stock`
        };

        const layout = {
            title: `Stock Price for ${ticker}`,
            plot_bgcolor: "#1e1e1e",
            paper_bgcolor: "#121212",
            font: { color: "#ffffff" },
            xaxis: { title: "Date", color: "#ffffff" },
            yaxis: { title: "Price (USD)", color: "#ffffff" },
            showlegend: true
        };

        Plotly.newPlot("stockGraph", [traceCandlestick], layout);
    }
});

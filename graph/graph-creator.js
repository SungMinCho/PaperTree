// create a network
var container = document.getElementById('mynetwork');

$.getJSON("graph.json", function (data) {
    var options = {
        edges: {
          font: {
            size: 14
          },
          length: 500,        },
        nodes: {
          shape: 'circle',
          margin: 10,
          widthConstraint: {
            maximum: 130
          }
        },
    };
    // initialize your network!
    var network = new vis.Network(container, data, options);
});


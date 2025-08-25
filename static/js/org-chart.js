// Organizational Chart Visualization using D3.js
(function() {
    'use strict';

    // Configuration
    const config = {
        width: 1200,
        height: 600,
        nodeWidth: 180,
        nodeHeight: 60,
        verticalSpacing: 100,
        horizontalSpacing: 200,
        colors: {
            'CEO_OFFICE': '#e74c3c',
            'CHIEF_DIRECTORATE': '#3498db', 
            'DIRECTORATE': '#2ecc71',
            'SUB_DIRECTORATE': '#f39c12'
        }
    };

    let svg, g, tree, root, zoom;

    function initChart() {
        const container = d3.select('#org-chart-container');
        
        // Clear any existing chart
        container.select('svg').remove();
        
        // Create SVG
        svg = container
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${config.width} ${config.height}`);

        // Add zoom behavior
        zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        svg.call(zoom);

        // Create main group
        g = svg.append('g');

        // Create tree layout
        tree = d3.tree()
            .size([config.width - 200, config.height - 200])
            .separation((a, b) => {
                return a.parent === b.parent ? 1 : 1.2;
            });
    }

    function loadData() {
        console.log('Loading org chart data...');
        fetch('/org-chart/data/')
            .then(response => {
                console.log('Response status:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Data received:', data);
                if (data.success) {
                    document.getElementById('loading').style.display = 'none';
                    renderChart(data.data);
                } else {
                    console.error('Failed to load org chart data:', data);
                    showError('Failed to load organizational data');
                }
            })
            .catch(error => {
                console.error('Error loading org chart data:', error);
                document.getElementById('loading').style.display = 'none';
                showError('Error loading organizational chart: ' + error.message);
            });
    }

    function showError(message) {
        const container = document.getElementById('org-chart-container');
        container.innerHTML = `
            <div class="d-flex justify-content-center align-items-center h-100">
                <div class="alert alert-danger" role="alert">
                    <i class="bi bi-exclamation-triangle"></i> ${message}
                </div>
            </div>
        `;
    }

    function renderChart(data) {
        // Convert flat data to hierarchy
        const hierarchy = d3.hierarchy({
            name: 'Organization',
            children: data
        });

        // Initialize all nodes as expanded
        hierarchy.descendants().forEach(d => {
            d._children = d.children;
        });

        root = hierarchy;
        root.x0 = config.height / 2;
        root.y0 = 0;

        update(root);
        centerChart();
    }

    function update(source) {
        // Compute the new tree layout
        const treeData = tree(root);
        const nodes = treeData.descendants();
        const links = treeData.descendants().slice(1);

        // Normalize for fixed-depth
        nodes.forEach(d => {
            d.y = d.depth * config.verticalSpacing;
        });

        // Update nodes
        const node = g.selectAll('g.node')
            .data(nodes, d => d.id || (d.id = ++i));

        // Enter new nodes
        const nodeEnter = node.enter().append('g')
            .attr('class', 'node')
            .attr('transform', d => `translate(${source.y0},${source.x0})`)
            .on('click', click);

        // Add rectangles for nodes
        nodeEnter.append('rect')
            .attr('width', config.nodeWidth)
            .attr('height', config.nodeHeight)
            .attr('x', -config.nodeWidth / 2)
            .attr('y', -config.nodeHeight / 2)
            .attr('rx', 5)
            .style('fill', d => d.data.type ? config.colors[d.data.type] : '#95a5a6')
            .style('stroke', '#34495e')
            .style('stroke-width', '2px')
            .style('cursor', 'pointer');

        // Add text labels
        nodeEnter.append('text')
            .attr('dy', '0.35em')
            .attr('text-anchor', 'middle')
            .style('fill', 'white')
            .style('font-weight', 'bold')
            .style('font-size', '12px')
            .text(d => d.data.name)
            .call(wrap, config.nodeWidth - 10);

        // Add expand/collapse indicators
        nodeEnter.append('circle')
            .attr('class', 'expand-indicator')
            .attr('r', 8)
            .attr('cy', config.nodeHeight / 2 + 15)
            .style('fill', '#34495e')
            .style('stroke', 'white')
            .style('stroke-width', '2px')
            .style('cursor', 'pointer')
            .style('display', d => d._children || d.children ? 'block' : 'none');

        nodeEnter.append('text')
            .attr('class', 'expand-text')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .attr('cy', config.nodeHeight / 2 + 15)
            .style('fill', 'white')
            .style('font-size', '12px')
            .style('font-weight', 'bold')
            .style('cursor', 'pointer')
            .style('display', d => d._children || d.children ? 'block' : 'none')
            .text(d => d._children ? '+' : '-');

        // Transition nodes to their new position
        const nodeUpdate = nodeEnter.merge(node);

        nodeUpdate.transition()
            .duration(750)
            .attr('transform', d => `translate(${d.y},${d.x})`);

        // Update expand/collapse indicators
        nodeUpdate.select('.expand-text')
            .text(d => d._children ? '+' : '-');

        // Remove exiting nodes
        const nodeExit = node.exit().transition()
            .duration(750)
            .attr('transform', d => `translate(${source.y},${source.x})`)
            .remove();

        // Update links
        const link = g.selectAll('path.link')
            .data(links, d => d.id);

        // Enter new links
        const linkEnter = link.enter().insert('path', 'g')
            .attr('class', 'link')
            .attr('d', d => {
                const o = {x: source.x0, y: source.y0};
                return diagonal(o, o);
            })
            .style('fill', 'none')
            .style('stroke', '#000')
            .style('stroke-width', '2px');

        // Transition links to their new position
        const linkUpdate = linkEnter.merge(link);

        linkUpdate.transition()
            .duration(750)
            .attr('d', d => diagonal(d, d.parent));

        // Remove exiting links
        link.exit().transition()
            .duration(750)
            .attr('d', d => {
                const o = {x: source.x, y: source.y};
                return diagonal(o, o);
            })
            .remove();

        // Store old positions for transition
        nodes.forEach(d => {
            d.x0 = d.x;
            d.y0 = d.y;
        });
    }

    // Toggle children on click
    function click(event, d) {
        if (d.children) {
            d._children = d.children;
            d.children = null;
        } else {
            d.children = d._children;
            d._children = null;
        }
        update(d);
    }

    // Create diagonal path
    function diagonal(s, d) {
        return `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                  ${(s.y + d.y) / 2} ${d.x},
                  ${d.y} ${d.x}`;
    }

    // Text wrapping function
    function wrap(text, width) {
        text.each(function() {
            const text = d3.select(this);
            const words = text.text().split(/\s+/).reverse();
            let word;
            let line = [];
            let lineNumber = 0;
            const lineHeight = 1.1;
            const y = text.attr('y');
            const dy = parseFloat(text.attr('dy'));
            let tspan = text.text(null).append('tspan').attr('x', 0).attr('y', y).attr('dy', dy + 'em');
            
            while (word = words.pop()) {
                line.push(word);
                tspan.text(line.join(' '));
                if (tspan.node().getComputedTextLength() > width) {
                    line.pop();
                    tspan.text(line.join(' '));
                    line = [word];
                    tspan = text.append('tspan').attr('x', 0).attr('y', y).attr('dy', ++lineNumber * lineHeight + dy + 'em').text(word);
                }
            }
        });
    }

    // Expand all nodes
    function expandAll() {
        root.descendants().forEach(d => {
            if (d._children) {
                d.children = d._children;
                d._children = null;
            }
        });
        update(root);
    }

    // Collapse all nodes except root
    function collapseAll() {
        root.descendants().forEach(d => {
            if (d.children && d.depth > 0) {
                d._children = d.children;
                d.children = null;
            }
        });
        update(root);
    }

    // Center the chart
    function centerChart() {
        const bounds = g.node().getBBox();
        const parent = svg.node().parentElement;
        const fullWidth = parent.clientWidth;
        const fullHeight = parent.clientHeight;
        const width = bounds.width;
        const height = bounds.height;
        const midX = bounds.x + width / 2;
        const midY = bounds.y + height / 2;
        
        const scale = 0.8 / Math.max(width / fullWidth, height / fullHeight);
        const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];
        
        svg.transition()
            .duration(750)
            .call(zoom.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));
    }

    // Counter for unique node IDs
    let i = 0;

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log('DOM loaded, initializing org chart...');

        // Check if D3 is loaded
        if (typeof d3 === 'undefined') {
            console.error('D3.js is not loaded!');
            showError('D3.js library failed to load. Please check your internet connection.');
            return;
        }

        console.log('D3.js version:', d3.version);

        initChart();
        loadData();

        // Event listeners for controls
        document.getElementById('expand-all').addEventListener('click', expandAll);
        document.getElementById('collapse-all').addEventListener('click', collapseAll);
        document.getElementById('center-chart').addEventListener('click', centerChart);
    });

})();

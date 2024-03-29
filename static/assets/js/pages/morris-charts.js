$(function(){
	Morris.Line({
	  element: 'line-example',
	  resize: true,
	  data: [
	    { y: '2006', a: 100, b: 90 , c: 21},
	    { y: '2007', a: 75,  b: 65 , c: 31},
	    { y: '2008', a: 50,  b: 40 , c: 41},
	    { y: '2009', a: 75,  b: 65 , c: 51},
	    { y: '2010', a: 50,  b: 40 , c: 61},
	    { y: '2011', a: 75,  b: 65 , c: 71},
	    { y: '2012', a: 100, b: 90, c: 81 }
	  ],
	  xkey: 'y',
	  ykeys: ['a', 'b', 'c'],
	  labels: ['CPU', 'Memory', 'Disk']
	});

	Morris.Area({
	  element: 'area-example',
	  resize: true,
	  data: [
	    { y: '2006', a: 100, b: 90 },
	    { y: '2007', a: 75,  b: 65 },
	    { y: '2008', a: 50,  b: 40 },
	    { y: '2009', a: 75,  b: 65 },
	    { y: '2010', a: 50,  b: 40 },
	    { y: '2011', a: 75,  b: 65 },
	    { y: '2012', a: 100, b: 90 }
	  ],
	  xkey: 'y',
	  ykeys: ['a', 'b'],
	  labels: ['Series A', 'Series B']
	});

	Morris.Bar({
	  element: 'bar-example',
	  resize: true,
	  data: [
	    { y: '2007', a: 75,  b: 65 },
	    { y: '2008', a: 50,  b: 40 },
	    { y: '2009', a: 75,  b: 65 },
	    { y: '2010', a: 50,  b: 40 },
	    { y: '2011', a: 75,  b: 65 }
	  ],
	  xkey: 'y',
	  ykeys: ['a', 'b'],
	  labels: ['Series A', 'Series B']
	});

	Morris.Donut({
	  element: 'donut-example',
	  resize: true,
	  data: [
	    {label: "Download Sales", value: 12},
	    {label: "In-Store Sales", value: 30},
	    {label: "Mail-Order Sales", value: 20}
	  ]
	});

});
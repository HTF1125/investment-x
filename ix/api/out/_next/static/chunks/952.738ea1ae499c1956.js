"use strict";(self.webpackChunk_N_E=self.webpackChunk_N_E||[]).push([[952],{4952:function(e,t,a){a.r(t),a.d(t,{default:function(){return c}});var n=a(7437),l=a(2265),i=a(5211),o=a(7346),r=a(5759),s=a(7161);a(3901);var d=a(3028);function c(e){let{data:t}=e,[a,i]=(0,l.useState)(null),r=(0,l.useRef)(null);return((0,l.useEffect)(()=>{if(!t)return;let e=Object.keys(t).map(e=>new Date(e)),a=Object.values(t),n=Array.from(new Set(a)),l=n.reduce((e,t,a)=>{let l=360*a/n.length;return e[t]="hsla(".concat(l,", 70%, 60%, 0.3)"),e},{}),o=e.map((t,n)=>({type:"box",xMin:t,xMax:n<e.length-1?e[n+1]:void 0,yMin:0,yMax:1,backgroundColor:l[a[n]],borderWidth:0}));i({data:{labels:e,datasets:[]},options:{responsive:!0,maintainAspectRatio:!1,scales:{x:{type:"time",time:{unit:"year",displayFormats:{year:"yyyy"}},title:{display:!0,text:"Date"},adapters:{date:{locale:d._}}},y:{display:!1,min:0,max:1}},plugins:{legend:{display:!0,position:"top",labels:{generateLabels:()=>n.map(e=>({text:e,fillStyle:l[e],strokeStyle:l[e],lineWidth:0,hidden:!1}))},onClick:()=>{}},tooltip:{mode:"index",intersect:!1,callbacks:{title:e=>e[0].label?new Date(e[0].label).toLocaleDateString("en-US",{year:"numeric",month:"long"}):"",label:e=>{let a=t[new Date(e.label).toISOString().split("T")[0]];return"Regime: ".concat(a)}}},annotation:{annotations:o},zoom:{pan:{enabled:!0,mode:"x"},zoom:{wheel:{enabled:!0},pinch:{enabled:!0},mode:"x"}}}}})},[t]),a)?(0,n.jsxs)("div",{children:[(0,n.jsx)("div",{style:{height:"400px",width:"100%"},children:(0,n.jsx)(o.kL,{ref:r,type:"line",data:a.data,options:a.options})}),(0,n.jsx)("button",{onClick:()=>{r.current&&r.current.resetZoom()},className:"mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 dark:bg-blue-700 dark:hover:bg-blue-800",children:"Reset Zoom"})]}):(0,n.jsx)("div",{children:"Loading chart..."})}i.kL.register(i.FB,i.f$,i.od,i.jn,i.Dx,i.u,i.De,r.Z,s.ZP)}}]);
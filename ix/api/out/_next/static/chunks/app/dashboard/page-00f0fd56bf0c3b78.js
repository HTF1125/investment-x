(self.webpackChunk_N_E=self.webpackChunk_N_E||[]).push([[702],{8786:function(e,t,r){Promise.resolve().then(r.bind(r,8562))},8562:function(e,t,r){"use strict";r.r(t),r.d(t,{default:function(){return h}});var a=r(7437),l=r(2265),s=r(665),d=r(4839),o=r(6164);function n(){for(var e=arguments.length,t=Array(e),r=0;r<e;r++)t[r]=arguments[r];return(0,o.m6)((0,d.W)(t))}let i=l.forwardRef((e,t)=>{let{className:r,...l}=e;return(0,a.jsx)("div",{className:"w-full overflow-auto",children:(0,a.jsx)("table",{ref:t,className:n("w-full caption-bottom text-sm",r),...l})})});i.displayName="Table";let c=l.forwardRef((e,t)=>{let{className:r,...l}=e;return(0,a.jsx)("thead",{ref:t,className:n("[&_tr]:border-b",r),...l})});c.displayName="TableHeader";let m=l.forwardRef((e,t)=>{let{className:r,...l}=e;return(0,a.jsx)("tbody",{ref:t,className:n("[&_tr:last-child]:border-0",r),...l})});m.displayName="TableBody",l.forwardRef((e,t)=>{let{className:r,...l}=e;return(0,a.jsx)("tfoot",{ref:t,className:n("bg-primary font-medium text-primary-foreground",r),...l})}).displayName="TableFooter";let x=l.forwardRef((e,t)=>{let{className:r,...l}=e;return(0,a.jsx)("tr",{ref:t,className:n("border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted",r),...l})});x.displayName="TableRow";let u=l.forwardRef((e,t)=>{let{className:r,...l}=e;return(0,a.jsx)("th",{ref:t,className:n("h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0",r),...l})});u.displayName="TableHead";let f=l.forwardRef((e,t)=>{let{className:r,...l}=e;return(0,a.jsx)("td",{ref:t,className:n("p-4 align-middle [&:has([role=checkbox])]:pr-0",r),...l})});async function p(e){return(0,s.b)("/api/data/performance/".concat(e))}function g(e){let{data:t,title:r}=e;return(0,a.jsxs)("div",{className:"mb-4 w-full",children:[(0,a.jsx)("h2",{className:"text-xl font-semibold mb-3 dark:text-gray-200",children:r}),(0,a.jsx)("div",{className:"overflow-x-auto",children:(0,a.jsxs)(i,{children:[(0,a.jsx)(c,{children:(0,a.jsxs)(x,{className:"dark:border-gray-700",children:[(0,a.jsx)(u,{className:"text-left text-sm px-2 py-1 dark:text-gray-300",children:"Index"}),(0,a.jsx)(u,{className:"text-right text-sm px-2 py-1 dark:text-gray-300",children:"Level"}),["1D","1W","1M","3M","6M","1Y","3Y","MTD","YTD"].map(e=>(0,a.jsx)(u,{className:"text-right text-sm px-2 py-1 dark:text-gray-300",children:e},e))]})}),(0,a.jsx)(m,{children:t.map(e=>{var t,r;return(0,a.jsxs)(x,{className:"hover:bg-gray-50 dark:hover:bg-gray-800 dark:border-gray-700",children:[(0,a.jsx)(f,{className:"font-medium text-sm px-2 py-1 dark:text-gray-300",children:e.index}),(0,a.jsx)(f,{className:"text-right text-sm px-2 py-1 dark:text-gray-300",children:null!==(r=null===(t=e.level)||void 0===t?void 0:t.toFixed(2))&&void 0!==r?r:"N/A"}),["1D","1W","1M","3M","6M","1Y","3Y","MTD","YTD"].map(t=>{var r,l;return(0,a.jsxs)(f,{className:"text-right text-sm px-2 py-1 ".concat(null!=e[t]&&e[t]>=0?"text-green-600 dark:text-green-400":"text-red-600 dark:text-red-400"),children:[null!==(l=null===(r=e[t])||void 0===r?void 0:r.toFixed(2))&&void 0!==l?l:"N/A","%"]},t)})]},e.index)})})]})})]})}function h(){let[e,t]=(0,l.useState)([]),[r,s]=(0,l.useState)(null),[d,o]=(0,l.useState)(!0);return((0,l.useEffect)(()=>{let e=[{group:"local-indices",title:"Local Indices"},{group:"global-markets",title:"Global Markets"},{group:"us-gics",title:"US GICS"},{group:"global-bonds",title:"Global Bonds"},{group:"currency",title:"Currency"},{group:"commodities",title:"Commodities"},{group:"theme",title:"Theme"}];Promise.all(e.map(e=>p(e.group))).then(r=>{t(r.map((t,r)=>({data:t,title:e[r].title}))),o(!1)}).catch(e=>{s(e instanceof Error?e.message:"An unknown error occurred"),console.error("Error fetching performance data:",e),o(!1)})},[]),d)?(0,a.jsx)("div",{className:"p-4 dark:bg-gray-900 dark:text-gray-200",children:"Loading..."}):r?(0,a.jsxs)("div",{className:"p-4 dark:bg-gray-900 text-red-600 dark:text-red-400",children:["Error: ",r]}):(0,a.jsx)("div",{className:"p-4 dark:bg-gray-900",children:(0,a.jsx)("div",{className:"w-[80%] mx-auto",children:(0,a.jsx)("div",{className:"flex flex-wrap -mx-4",children:e.map((e,t)=>(0,a.jsx)("div",{className:"w-full md:w-1/2 px-4 mb-8",children:(0,a.jsx)("div",{className:"overflow-x-auto bg-white dark:bg-gray-800 p-4 rounded-lg shadow-md",children:(0,a.jsx)(g,{data:e.data,title:e.title})})},t))})})})}f.displayName="TableCell",l.forwardRef((e,t)=>{let{className:r,...l}=e;return(0,a.jsx)("caption",{ref:t,className:n("mt-4 text-sm text-muted-foreground",r),...l})}).displayName="TableCaption"},665:function(e,t,r){"use strict";async function a(e,t){let r={...t,next:{revalidate:60}},a=await fetch(e,r);if(!a.ok){let e=await a.text();throw Error("HTTP error! status: ".concat(a.status,", body: ").concat(e))}return a.json()}r.d(t,{b:function(){return a}})}},function(e){e.O(0,[868,971,23,744],function(){return e(e.s=8786)}),_N_E=e.O()}]);
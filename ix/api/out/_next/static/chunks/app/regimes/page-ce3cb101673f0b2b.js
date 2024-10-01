(self.webpackChunk_N_E=self.webpackChunk_N_E||[]).push([[174],{9341:function(e,t,r){Promise.resolve().then(r.bind(r,2282))},551:function(e,t,r){"use strict";Object.defineProperty(t,"__esModule",{value:!0}),Object.defineProperty(t,"default",{enumerable:!0,get:function(){return a}});let n=r(9920);r(7437),r(2265);let l=n._(r(148));function a(e,t){var r;let n={loading:e=>{let{error:t,isLoading:r,pastDelay:n}=e;return null}};"function"==typeof e&&(n.loader=e);let a={...n,...t};return(0,l.default)({...a,modules:null==(r=a.loadableGenerated)?void 0:r.modules})}("function"==typeof t.default||"object"==typeof t.default&&null!==t.default)&&void 0===t.default.__esModule&&(Object.defineProperty(t.default,"__esModule",{value:!0}),Object.assign(t.default,t),e.exports=t.default)},912:function(e,t,r){"use strict";Object.defineProperty(t,"__esModule",{value:!0}),Object.defineProperty(t,"BailoutToCSR",{enumerable:!0,get:function(){return l}});let n=r(5592);function l(e){let{reason:t,children:r}=e;if("undefined"==typeof window)throw new n.BailoutToCSRError(t);return r}},148:function(e,t,r){"use strict";Object.defineProperty(t,"__esModule",{value:!0}),Object.defineProperty(t,"default",{enumerable:!0,get:function(){return o}});let n=r(7437),l=r(2265),a=r(912),d=r(1481);function s(e){return{default:e&&"default"in e?e.default:e}}let i={loader:()=>Promise.resolve(s(()=>null)),loading:null,ssr:!0},o=function(e){let t={...i,...e},r=(0,l.lazy)(()=>t.loader().then(s)),o=t.loading;function u(e){let s=o?(0,n.jsx)(o,{isLoading:!0,pastDelay:!0,error:null}):null,i=t.ssr?(0,n.jsxs)(n.Fragment,{children:["undefined"==typeof window?(0,n.jsx)(d.PreloadCss,{moduleIds:t.modules}):null,(0,n.jsx)(r,{...e})]}):(0,n.jsx)(a.BailoutToCSR,{reason:"next/dynamic",children:(0,n.jsx)(r,{...e})});return(0,n.jsx)(l.Suspense,{fallback:s,children:i})}return u.displayName="LoadableComponent",u}},1481:function(e,t,r){"use strict";Object.defineProperty(t,"__esModule",{value:!0}),Object.defineProperty(t,"PreloadCss",{enumerable:!0,get:function(){return a}});let n=r(7437),l=r(8512);function a(e){let{moduleIds:t}=e;if("undefined"!=typeof window)return null;let r=(0,l.getExpectedRequestStore)("next/dynamic css"),a=[];if(r.reactLoadableManifest&&t){let e=r.reactLoadableManifest;for(let r of t){if(!e[r])continue;let t=e[r].files.filter(e=>e.endsWith(".css"));a.push(...t)}}return 0===a.length?null:(0,n.jsx)(n.Fragment,{children:a.map(e=>(0,n.jsx)("link",{precedence:"dynamic",rel:"stylesheet",href:r.assetPrefix+"/_next/"+encodeURI(e),as:"style"},e))})}},2282:function(e,t,r){"use strict";r.r(t),r.d(t,{default:function(){return u}});var n=r(7437),l=r(2265),a=r(5810);async function d(){try{let e=a.T?"".concat(a.T,"/api/data/regimes"):"/api/data/regimes",t=await fetch(e,{next:{revalidate:60}});if(!t.ok)throw Error("HTTP error! status: ".concat(t.status));return await t.json()}catch(e){return console.error("Error fetching regimes:",e),[]}}var s=r(551);let i=r.n(s)()(()=>Promise.all([r.e(674),r.e(739),r.e(208),r.e(952)]).then(r.bind(r,4952)),{loadableGenerated:{webpack:()=>[4952]},ssr:!1,loading:()=>(0,n.jsx)("p",{children:"Loading Chart..."})});function o(e){let{regimes:t,selectedRegime:r,onRegimeChange:l}=e;return(0,n.jsxs)("div",{className:"mb-4",children:[(0,n.jsx)("label",{htmlFor:"regime-select",className:"block text-sm font-medium mb-2 dark:text-gray-200",children:"Select Regime:"}),(0,n.jsx)("select",{id:"regime-select",value:(null==r?void 0:r.code)||"",onChange:e=>{let r=t.find(t=>t.code===e.target.value);r&&l(r)},className:"w-full pl-3 pr-10 py-2 text-sm border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200",children:t.map(e=>(0,n.jsx)("option",{value:e.code,children:e.code},e.code))})]})}function u(){let[e,t]=(0,l.useState)([]),[r,a]=(0,l.useState)(null),[s,u]=(0,l.useState)(!0),[c,f]=(0,l.useState)(null);return((0,l.useEffect)(()=>{d().then(e=>{t(e),e.length>0&&a(e[0]),u(!1)}).catch(e=>{console.error("Error fetching regime data:",e),f("Failed to fetch regime data"),u(!1)})},[]),s)?(0,n.jsx)("div",{className:"w-full p-4 dark:bg-gray-900 dark:text-gray-200",children:"Loading..."}):c?(0,n.jsxs)("div",{className:"w-full p-4 dark:bg-gray-900 text-red-600 dark:text-red-400",children:["Error: ",c]}):0===e.length?(0,n.jsx)("div",{className:"w-full p-4 dark:bg-gray-900 dark:text-gray-200",children:"No regime data available"}):(0,n.jsx)("div",{className:"w-full p-4 dark:bg-gray-900",children:(0,n.jsxs)("div",{className:"w-[90%] mx-auto",children:[(0,n.jsx)("h1",{className:"text-2xl font-bold mb-4 dark:text-gray-200",children:"Regimes"}),(0,n.jsxs)("div",{className:"bg-white dark:bg-gray-800 p-4 rounded-lg shadow-md",children:[(0,n.jsx)(o,{regimes:e,selectedRegime:r,onRegimeChange:a}),r&&(0,n.jsx)("div",{className:"mt-4",children:(0,n.jsx)(i,{data:r.data})})]})]})})}},5810:function(e,t,r){"use strict";r.d(t,{T:function(){return n}});let n=""}},function(e){e.O(0,[971,23,744],function(){return e(e.s=9341)}),_N_E=e.O()}]);
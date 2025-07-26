import './index.css'

import { createApp } from 'vue'
import router from './router'
import App from './App.vue'

import { 
  Button, 
  ListView, 
  Dialog, 
  FeatherIcon, 
  Autocomplete, 
  setConfig, 
  frappeRequest, 
  resourcesPlugin 
} from 'frappe-ui'

let app = createApp(App)

setConfig('resourceFetcher', frappeRequest)

app.use(router)
app.use(resourcesPlugin)

app.component('Button', Button)
app.component('ListView', ListView)
app.component('Dialog', Dialog)
app.component('FeatherIcon', FeatherIcon)
app.component('Autocomplete', Autocomplete)

app.mount('#app')

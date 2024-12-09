<template>
  <div id="app">
    <h1>VMware to OpenStack migration</h1>
    <input v-model="vmName" placeholder="Enter VM Name" />
    <button @click="fetchVmDetails">Migrate</button>
    <div v-if="loading" class="progress-bar">
      <div class="progress-bar-inner">Migrating...</div>
    </div>
    <div v-if="vmDetails" class="vm-details">
      <h2>VM Name: {{ vmDetails.name }}</h2>
      <table>
        <tr>
          <th>Attribute</th>
          <th>Value</th>
        </tr>
        <tr>
          <td>CPU</td>
          <td>{{ vmDetails.cpu }} vCPUs</td>
        </tr>
        <tr>
          <td>Memory</td>
          <td>{{ vmDetails.memory }} MB</td>
        </tr>
        <tr>
          <td>Power State</td>
          <td>{{ vmDetails.power_state }}</td>
        </tr>
        <tr>
          <td>IP Address</td>
          <td>{{ vmDetails.ip_address }}</td>
        </tr>
      </table>
      <h3>Datastores:</h3>
      <table>
        <tr>
          <th>Datastore Name</th>
          <th>Remote Host</th>
          <th>Remote Path</th>
          <th>Capacity</th>
          <th>Free Space</th>
          <th>Accessible</th>
        </tr>
        <tr v-for="datastore in vmDetails.datastores" :key="datastore.name">
          <td>{{ datastore.name }}</td>
          <td>{{ datastore.remote_host }}</td>
          <td>{{ datastore.remote_path }}</td>
          <td>{{ datastore.capacity }} bytes</td>
          <td>{{ datastore.free_space }} bytes</td>
          <td>{{ datastore.accessible }}</td>
        </tr>
      </table>
      <h3>Files:</h3>
      <table>
        <tr>
          <th>Path</th>
          <th>Size</th>
          <th>Type</th>
        </tr>
        <tr v-for="file in vmDetails.files" :key="file.path">
          <td>{{ file.path }}</td>
          <td>{{ file.size }} bytes</td>
          <td>{{ file.type }}</td>
        </tr>
      </table>
    </div>
    <div v-if="error">
      <p style="color: red;">{{ error }}</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      vmName: '',
      vmDetails: null,
      error: null,
      loading: false,
    };
  },
  methods: {
    async fetchVmDetails() {
      this.loading = true;
      try {
        const response = await axios.get('http://localhost:5000/vm-details', {
          params: { vm_name: this.vmName },
        });
        this.vmDetails = response.data;
        this.error = null;
      } catch (err) {
        this.vmDetails = null;
        this.error = err.response ? err.response.data.error : 'An error occurred';
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
input {
  padding: 10px;
  margin-right: 10px;
}
button {
  padding: 10px;
}
.vm-details {
  margin-top: 20px;
}
table {
  width: 80%;
  margin: 20px auto;
  border-collapse: collapse;
}
th, td {
  border: 1px solid #ddd;
  padding: 8px;
}
th {
  background-color: #f2f2f2;
  color: black;
}
tr:nth-child(even) {
  background-color: #f9f9f9;
}
tr:hover {
  background-color: #ddd;
}
td {
  text-align: left;
}
.progress-bar {
  width: 80%;
  margin: 20px auto;
  background-color: #f3f3f3;
  border: 1px solid #ccc;
  border-radius: 4px;
  overflow: hidden;
}
.progress-bar-inner {
  width: 100%;
  height: 30px;
  background-color: #4caf50;
  color: white;
  text-align: center;
  line-height: 30px;
  font-weight: bold;
  animation: progress 2s infinite;
}
@keyframes progress {
  0% { width: 0; }
  100% { width: 100%; }
}
</style>
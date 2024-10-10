import axios from "axios";

export const axiosDefault = axios.create({
    baseURL: `${window.location.protocol}//${window.location.host}/api`,
    headers: {
        'Content-Type': 'application/json'
    },
})

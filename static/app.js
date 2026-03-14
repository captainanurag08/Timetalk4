/* ===============================
GLOBAL VARIABLES
=================================*/

let chosenSlot = null
let timer = null
let time = 1500


/* ===============================
FIND FREE SLOT
=================================*/

async function findSlot(){

let day = document.getElementById("day").value
let duration = document.getElementById("duration").value
let start = document.getElementById("start").value
let end = document.getElementById("end").value

if(!duration || !start || !end){
alert("Please fill all fields")
return
}

let res = await fetch("/find_slot",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
day:day,
duration:duration,
start:start,
end:end
})
})

let data = await res.json()

let html=""

if(data.length==0){

html="<p>No free slots found</p>"

}else{

data.forEach(s=>{

html += `
<div style="border:1px solid #ccc;padding:10px;margin:10px;border-radius:8px">

<span>🕒 <b>${s.start} - ${s.end}</b></span>

<button onclick="chooseSlot('${day}','${s.start}','${s.end}')"
style="margin-left:20px;padding:5px 10px;cursor:pointer">
Add Task
</button>

</div>
`

})

}

document.getElementById("result").innerHTML=html

}


/* ===============================
CHOOSE SLOT
=================================*/

function chooseSlot(day,start,end){

let title = prompt("Enter task title")

if(!title) return

let priority = prompt("Priority (Low/Medium/High)","Medium")

addTask(title,day,start,end,priority)

}


/* ===============================
ADD TASK FROM SLOT
=================================*/

function addTask(title,day,start,end,priority){

fetch("/add_auto",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
title:title,
day:day,
start:start,
end:end,
priority:priority
})
})
.then(res=>res.json())
.then(()=>{

alert("Task added successfully")

window.location="/schedule"

})

}


/* ===============================
WEEKLY AUTO SCHEDULER
=================================*/

function weeklyAuto(){

let title = document.getElementById("wtitle").value
let duration = document.getElementById("wduration").value
let priority = document.getElementById("wpriority") ?
document.getElementById("wpriority").value : "Medium"

if(!title || !duration){

alert("Enter task name and duration")
return

}

fetch("/weekly_auto",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
title:title,
duration:duration,
priority:priority
})
})
.then(res=>res.json())
.then(()=>{

alert("Weekly tasks created")

})

}

/*deadline   */

async function addDeadline(){

let res = await fetch("/add_deadline",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({
title:document.getElementById("title").value,
deadline:document.getElementById("deadline").value
})
})

if(!res.ok){
let text = await res.text()
console.log(text)
alert("Server error. Check terminal.")
return
}

let data = await res.json()

alert("Deadline added!")
location.reload()

}



/* ===============================
MANUAL WEEKLY TASK
=================================*/



function manualWeekly(){

let title = document.getElementById("mtitle").value
let day = document.getElementById("mday").value
let start = document.getElementById("mstart").value
let end = document.getElementById("mend").value
let priority = document.getElementById("mpriority").value

fetch("/manual-weekly",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
title:title,
day:day,
start:start,
end:end,
priority:priority
})
})
.then(r=>r.json())
.then(()=>{

alert("Weekly task added")

})

}




/* home deadline */
/* home deadline */
/* home deadline */
/* Fixed Load Deadlines */
async function loadDeadlines() {
    const box = document.getElementById("deadlineBox");
    if (!box) return; // Exit quietly if not on the home page

    try {
        const res = await fetch("/deadlines_home");
        const data = await res.json();
        
        if (!data || data.length === 0) {
            box.innerHTML = "<p style='opacity:0.7'>No deadlines yet </p>";
            return;
        }

        let html = "";
        data.forEach(d => {
            let color = "#1cb633"; // Green
            if (d.days_left < 3) color = "#f44336"; // Red
            else if (d.days_left < 7) color = "#ff9800"; // Orange

            html += `
                <div class="card" style="border-left: 5px solid ${color}; margin-bottom: 10px; padding: 10px; display: block;">
                    <b style="color: #f7f3f3;">${d.title}</b>
                    <p style="margin: 5px 0; color: #e4dcdc;"> Due: ${d.deadline}</p>
                    <p style="font-weight: bold; color: ${color}; margin: 0;">
                        ${d.days_left} days remaining
                    </p>
                    <button onclick="deleteDeadline(${d.id})" 
                            style="margin-top:10px; padding:4px 12px; cursor:pointer; background:#f44336; color:white; border:none; border-radius:4px; font-size: 0.8em;">
                        Cancel
                    </button>
                </div>`;
        });
        box.innerHTML = html;
    } catch (err) {
        console.error("Fetch error:", err);
        box.innerHTML = "<p style='color:red'>Error loading deadlines.</p>";
    }
}

/* Fixed Delete Function */
async function deleteDeadline(id) {
    if (!confirm("Are you sure you want to remove this deadline?")) return;

    try {
        const res = await fetch("/delete_deadline", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: id })
        });

        const data = await res.json();
        alert(data.msg);
        loadDeadlines(); // Refresh the list
    } catch (err) {
        alert("Delete failed. Check console.");
    }
}

// Add this at the very bottom of app.js to trigger the load
document.addEventListener("DOMContentLoaded", () => {
    loadDeadlines();
});
     

           
         

/*auto scheduler */



async function autoSchedule(){

let title = document.getElementById("auto_title").value
let hours = document.getElementById("auto_hours").value
let deadline = document.getElementById("auto_deadline").value

if(!title || !hours || !deadline){
alert("Fill all fields")
return
}

let res = await fetch("/auto_schedule",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({
title:title,
hours:hours,
deadline:deadline
})
})

let data = await res.json()

alert(data.msg)

location.reload()

}

/* ===============================
FOCUS TIMER
=================================*/

function startTimer(){

if(Notification.permission !== "granted"){
Notification.requestPermission()
}

if(timer) return

timer=setInterval(()=>{

time--

let minutes=Math.floor(time/60)
let seconds=time%60

let timerBox=document.getElementById("timer")

if(timerBox){

timerBox.innerText=
String(minutes).padStart(2,"0")+":"+
String(seconds).padStart(2,"0")

}

if(time<=0){

clearInterval(timer)
timer=null

new Notification("Focus session finished!")

}

},1000)

}


function resetTimer(){

clearInterval(timer)

timer=null
time=1500

let timerBox=document.getElementById("timer")

if(timerBox){
timerBox.innerText="25:00"
}

}


/*debt timer*/

async function addDebt(){

let hours = document.getElementById("debt_hours").value || 0
let minutes = document.getElementById("debt_minutes").value || 0

let res = await fetch("/add_debt",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({
hours:hours,
minutes:minutes
})
})

let data = await res.json()

alert(data.msg)

}

/*delete function on jsdeadline*/
async function deleteDeadline(id){

if(!confirm("Cancel this deadline?")) return

let res = await fetch("/delete_deadline",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({
id:id
})
})

let data = await res.json()

alert(data.msg)

loadDeadlines()

}


/*  debt timer on week page*/
async function loadDebt(){

let res = await fetch("/get_debt")

let data = await res.json()

document.getElementById("debtBox").innerHTML =
"⏳ Time Debt: "+data.hours+"h "+data.minutes+"m"

}

document.addEventListener("DOMContentLoaded",loadDebt)


/* ===============================
TASK REMINDER
=================================*/

function checkTasks(){

fetch("/tasks_today")
.then(res=>res.json())
.then(tasks=>{

let now=new Date()

tasks.forEach(task=>{

let parts=task.start.split(":")
let taskTime=new Date()

taskTime.setHours(parts[0])
taskTime.setMinutes(parts[1])
taskTime.setSeconds(0)

let diff=(taskTime-now)/60000

if(diff>0 && diff<1){

if(Notification.permission==="granted"){

new Notification(
"Upcoming Task: "+task.title,
{
body:"Starting at "+task.start
}
)

}

}

})

})

}


/* ===============================
START TASK CHECK LOOP
=================================*/

setInterval(checkTasks,60000)


/* ===============================
REQUEST NOTIFICATION PERMISSION
=================================*/

document.addEventListener("DOMContentLoaded",function(){

if(Notification.permission!=="granted"){
Notification.requestPermission()
}

})
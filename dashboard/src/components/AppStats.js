import React, { useEffect, useState } from 'react'
import '../App.css';

export default function AppStats() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [stats, setStats] = useState({});
    const [error, setError] = useState(null)

	const getStats = () => {
	
        fetch(`http://kevin-3855.eastus.cloudapp.azure.com/processing/Usage_Count/stats`)
            .then(res => res.json())
            .then((result)=>{
				console.log("Received Stats")
                setStats(result);
                setIsLoaded(true);
            },(error) =>{
                setError(error)
                setIsLoaded(true);
            })
    }
    useEffect(() => {
		const interval = setInterval(() => getStats(), 2000); // Update every 2 seconds
		return() => clearInterval(interval);
    }, [getStats]);

    if (error){
        return (<div className={"error"}>Error found when fetching from API</div>)
    } else if (isLoaded === false){
        return(<div>Loading...</div>)
    } else if (isLoaded === true){
        return(
            <div>
                <h1>Latest Stats</h1>
                <table className={"StatsTable"}>
					<tbody>
						<tr>
							<th>Items</th>
							<th>Abilities</th>
						</tr>
						<tr>
							<td># Item readings: {stats['num_item_readings']}</td>
							<td># Ability readings: {stats['num_ability_readings']}</td>
						</tr>
						<tr>
							<td colspan="2">Max ability reading: {stats['max_ability_reading']}</td>
						</tr>
						<tr>
							<td colspan="2">Max item reading: {stats['max_item_reading']}</td>
						</tr>
						<tr>
							<td colspan="2">Total readings: {stats['num_total_readings']}</td>
						</tr>
					</tbody>
                </table>
                <h3>Last Updated: {stats['last_updated']}</h3>

            </div>
        )
    }
}

# README

 > Add a python script to projects/getting-started that investigates a satellite-hub network system with measles transmission. Add some figures showing how transmission is propgated through the network. use laser-measles to build the model.

● All 4 figures are generated and the results look correct:                                                                                
                                                                                                                                           
  1. Epidemic curves — Hub peaks first (~day 120, ~60k infected), satellites follow with delayed, smaller peaks proportional to their      
  population                                                                                                                               
  2. Spatial spread — Generally increasing arrival time with distance (day 33–74), showing the wave propagation from hub to satellites     
  3. Attack rates — All patches reach ~93-94% attack rates, consistent with a fully susceptible population (mcv1=0) and R0=2.5             
                                                            
  The script is complete at projects/getting-started/satellite_hub_measles.py. It creates a 7-patch satellite-hub network, runs a 365-day
  SEIR simulation with gravity-based spatial mixing, and produces 4 figures in projects/getting-started/figures/.